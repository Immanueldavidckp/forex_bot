"""
engine/dashboard.py — the V5 chart dashboard: every symbol × H4 / H1 / M30 / M15 / M5 with the strategy's
marks (H1 bias swings, M15 supply/demand, displacement, FVG, mitigation block, M5 retracement and BOS,
entry / SL / TP / Target 1 / layer), the live book, and the controls: trading on/off, cancel a setup,
close a setup or a position.

    python3 -m engine.dashboard [--port 8770]          http://127.0.0.1:8770 (loopback only), /backtest = the backtest,
                                                       /smc = SMC Zones + LuxAlgo next to the V5 engine (smc_compare.py)
    python3 -m engine.dashboard --port 8771 --public   copy for the internet (Cloudflare tunnel): no trading / MT5 /
                                                       close buttons (those POSTs refused), MT5 login number hidden;
                                                       /learn labels can be drawn and saved (marked "by": "public")

It reads only the files the engine writes (engine_data/overview.json, view/<SYMBOL>.json) and never talks
to MT5. Controls are appended to engine_data/commands.jsonl; the running engine applies them within one
loop (15 s). POSTs need the X-V5 header, which a page from another site cannot send without a CORS
preflight this server never answers, so only this page can press the buttons.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .config import COMMANDS_FILE, DATA_DIR, HERE, OVERVIEW_FILE, VIEW_DIR, PNL_FILE

BT_DIR = os.path.join(DATA_DIR, "backtest")          # written by engine.backtest / bt_report / bt_charts

ACTIONS = {"trading", "cancel_setup", "close_setup", "close_ticket", "mt5", "kronos", "kronos_close", "sdd", "fib", "sdd_layers"}
KRONOS_DIR = os.path.join(DATA_DIR, "kronos")
SDD_STATE = os.path.join(DATA_DIR, "sdd", "state.json")                # engine/sdd_book.py → the /smc trade list
FIB_STATE = os.path.join(DATA_DIR, "fib", "state.json")                # engine/fib_book.py → the /smc Fib list
FIB_BT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research", "fib_trend", "results.json")  # its backtest
KRONOS_VIEW = os.path.join(KRONOS_DIR, "view.json")              # engine/kronos_book.py → the /kronos page
MT5_OPS = {"start", "stop", "restart", "login"}
SYM = re.compile(r"^[A-Za-z0-9._#-]{1,24}$")
SETUP_ID = re.compile(r"^[A-Za-z0-9._#-]{1,24}-(M5|M15|M30|H1|H4)-[DS]-\d{6,12}$")
# --public: the control buttons are hidden (the server refuses the POSTs anyway)
PUBLIC_CSS = (b"<style>#trading,#room-toggle,#mt5-restart,#mt5-stop,#mt5-start,[data-close],[data-ticket],[data-cancel],"
              b"[data-closeset]{display:none!important}</style>")
# the learn page on the public copy: anyone with the link may LOOK, but drawing needs the secret key in the
# URL (?key=...) — the labels are training ground truth, and the tunnel link may travel (2026-10-25)
PUBLIC_LEARN_CSS = b"<style>#tools,#noteBox,.x,footer{display:none!important}</style>"
PUBLIC_KRONOS_CSS = b"<style>#kronos-toggle,[data-kclose]{display:none!important}</style>"
LEARN_KEY_FILE = os.path.join(DATA_DIR, "learn", "key.txt")


def learn_key() -> str:
    try:
        with open(LEARN_KEY_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        os.makedirs(os.path.dirname(LEARN_KEY_FILE), exist_ok=True)
        k = secrets.token_hex(8)
        with open(LEARN_KEY_FILE, "w") as f:
            f.write(k)
        return k


TF_MS = {"M5": 300_000, "M15": 900_000, "M30": 1_800_000, "H1": 3_600_000, "H4": 14_400_000}
_HIST = {}          # (sym, tf) → (file mtime, bars): the saved history files are big, parse each once


def _tf_bars(sym: str, tf: str) -> list:
    """Chart bars [t_s, o, h, l, c] on timeframe `tf`: the engine's own fresh view bars (engine_data/view, up to now) with the
    older saved FxPro history put in front when it joins them without a gap."""
    with open(os.path.join(VIEW_DIR, f"{sym}.json")) as f:
        fresh = [b[:5] for b in json.load(f)["bars"][tf]]
    if not fresh:
        raise FileNotFoundError(sym)
    old = []
    path = os.path.join(DATA_DIR, "history", f"{sym}.json")
    try:
        mt = os.path.getmtime(path)
        if _HIST.get((sym, tf), (0,))[0] != mt:
            with open(path) as f:
                _HIST[(sym, tf)] = (mt, json.load(f)["bars"].get(tf, [])[-3000:])
        old = [[b[0] // 1000] + b[1:5] for b in _HIST[(sym, tf)][1] if b[0] // 1000 < fresh[0][0]]
    except FileNotFoundError:
        pass
    if old and fresh[0][0] - old[-1][0] > TF_MS[tf] // 1000 * 3:      # the history stops days before: a hole, leave it out
        old = []
    return (old + fresh)[-900:]


def _signal(sym: str):
    try:
        with open(os.path.join(KRONOS_DIR, "signals.json")) as f:
            return json.load(f).get(sym)
    except (FileNotFoundError, ValueError):
        return None


def kronos_chart(sym: str, tf: str = "M15") -> bytes:
    """The /kronos big chart: every bar Kronos read (feed/<SYM>.json), its latest forecast with each path, and the
    symbol's last 80 forecasts (the tail of signals.jsonl) to lay over the candles they forecast."""
    with open(os.path.join(KRONOS_DIR, "feed", f"{sym}.json")) as f:
        raw = json.load(f)["bars"]
    if tf != "M15":                                   # other timeframes: candles only (Kronos forecasts M15)
        try:
            bars = _tf_bars(sym, tf)
        except (FileNotFoundError, KeyError):
            return json.dumps({"error": "no bars for " + sym + " on " + tf}).encode()
        return json.dumps({"symbol": sym, "tf": tf, "bars": bars, "signal": _signal(sym), "history": []}).encode()
    bars = [[r[0] // 1000, r[1], r[2], r[3], r[4]] for r in raw]
    sig = _signal(sym)
    hist = []
    try:
        with open(os.path.join(KRONOS_DIR, "signals.jsonl"), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 2_000_000))
            lines = f.read().splitlines()[1:]
        for line in reversed(lines):
            if f'"symbol": "{sym}"'.encode() not in line:
                continue
            try:
                h = json.loads(line)
            except ValueError:
                continue
            hist.append({k: h.get(k) for k in ("bar_t", "last", "p_up", "median", "q10", "q90")})
            if len(hist) >= 80:
                break
    except FileNotFoundError:
        pass
    return json.dumps({"symbol": sym, "tf": "M15", "bars": bars, "signal": sig, "history": hist[::-1]}).encode()


_FEED_T = {}        # sym → (mtime, rows, last bar t_ms)
_GPU = [0.0, None]  # (checked at, {util, mem_used, mem_total})


def _procs(needle: str) -> list:
    out = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
            if needle in cmd and "zsh -c" not in cmd:
                with open(f"/proc/{pid}/stat") as f:
                    st = f.read().rsplit(")", 1)[1].split()
                with open("/proc/uptime") as f:
                    up = float(f.read().split()[0])
                out.append({"pid": int(pid), "cmd": cmd.strip()[:160], "full": cmd.strip(),
                            "age_s": round(up - int(st[19]) / os.sysconf("SC_CLK_TCK"))})
        except (OSError, IndexError, ValueError):
            continue
    return out


def _gpu():
    import subprocess, time as _t
    if _t.time() - _GPU[0] < 3:
        return _GPU[1]
    _GPU[0] = _t.time()
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4).stdout.split(",")
        _GPU[1] = {"name": r[0].strip(), "util": int(r[1]), "mem_used": int(r[2]), "mem_total": int(r[3]), "temp": int(r[4])}
    except Exception:
        _GPU[1] = None
    return _GPU[1]


def kronos_status() -> bytes:
    """The /kronos 'forecaster' panel: is concepter.kronos.signals alive, what the GPU is working on now, how long one chart /
    one candle takes (the `secs` of each GPU pass in signals.jsonl, ÷ the charts in the pass), and each symbol's state."""
    import time as _t
    from .config import KRONOS as K
    now = int(_t.time() * 1000)
    try:
        with open(os.path.join(KRONOS_DIR, "signals.json")) as f:
            sigs = json.load(f)
    except (FileNotFoundError, ValueError):
        sigs = {}
    chunk, bar_ms = 4, 900_000
    procs = _procs("concepter.kronos.signals")
    # the running forecaster may serve a shorter list (signals.py --symbols; David 2026-11-08: crypto only on a Sunday)
    today = None
    for p in procs:
        if "--symbols" in p["full"]:
            today = [x for x in p["full"].split("--symbols", 1)[1].strip().split()[0].split(",") if x]
    rows = []
    for sym in K["SYMBOLS"]:
        fp = os.path.join(KRONOS_DIR, "feed", f"{sym}.json")
        try:
            mt = os.path.getmtime(fp)
            if _FEED_T.get(sym, (0,))[0] != mt:
                with open(fp) as f:
                    b = json.load(f)["bars"]
                _FEED_T[sym] = (mt, len(b), b[-1][0] if b else None)
            _, n, ft = _FEED_T[sym]
        except (OSError, ValueError, KeyError):
            n, ft = 0, None
        sg = sigs.get(sym) or {}
        st = ("off today" if today is not None and sym not in today else
              "no feed" if not ft or n < K["CONTEXT"] else "forecast" if sg.get("bar_t") == ft else "queued")
        rows.append({"symbol": sym, "feed_t": ft, "feed_bars": n, "state": st, "bar_t": sg.get("bar_t"),
                     "made_ms": sg.get("made_ms"), "secs": sg.get("secs"), "p_up": sg.get("p_up")})
    others = [{"pid": p["pid"], "name": p["cmd"].split("concepter.kronos.")[-1].split()[0]}
              for n in ("concepter.kronos.zone_touch", "concepter.kronos.zone_backtest", "concepter.kronos.evaluate")
              for p in _procs(n)]
    # timing: one record per symbol, a GPU pass = the records written together (same made_ms second, same secs)
    passes = []
    try:
        with open(os.path.join(KRONOS_DIR, "signals.jsonl"), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 300_000))
            lines = f.read().splitlines()[1:]
        cur = None
        for line in lines:
            try:
                h = json.loads(line)
            except ValueError:
                continue
            if h.get("secs") is None or h.get("made_ms") is None:
                continue
            if cur and cur["secs"] == h["secs"] and abs(cur["made_ms"] - h["made_ms"]) < 3000:
                cur["n"] += 1
            else:
                cur = {"secs": h["secs"], "made_ms": h["made_ms"], "n": 1}
                passes.append(cur)
    except FileNotFoundError:
        pass
    last = passes[-12:]
    per_chart = [p["secs"] / p["n"] for p in last[-4:]]
    best = min((p["secs"] / p["n"] for p in last), default=None)
    avg_chart = sum(per_chart) / len(per_chart) if per_chart else None
    pending = [r["symbol"] for r in rows if r["state"] == "queued"]
    running = pending[:chunk] if procs else []
    t_end = max([r["made_ms"] or 0 for r in rows] + [(now - procs[0]["age_s"] * 1000) if procs else 0])
    try:
        with open(os.path.join(KRONOS_DIR, "signals.log"), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 3000))
            tail = f.read().decode(errors="replace").splitlines()[-8:]
    except FileNotFoundError:
        tail = []
    return json.dumps({
        "now": now, "alive": bool(procs), "pid": procs[0]["pid"] if procs else None,
        "uptime_s": procs[0]["age_s"] if procs else None, "gpu": _gpu(), "shares_gpu_with": others,
        "model": "Kronos-base", "tf": K["TF"], "paths": K["PATHS"], "horizon": K["HORIZON"], "context": K["CONTEXT"], "chunk": chunk,
        "symbols": rows, "pending": pending, "running": running, "running_since": t_end if running else None,
        "today": today, "off_today": [r["symbol"] for r in rows if r["state"] == "off today"],
        "per_chart_s": avg_chart, "best_chart_s": best, "per_candle_s": avg_chart / K["HORIZON"] if avg_chart else None,
        "last_pass": last[-1] if last else None, "passes": [[p["made_ms"], p["secs"], p["n"]] for p in last],
        "eta_s": round(avg_chart * len(pending)) if avg_chart else None,
        "full_cycle_s": round(avg_chart * len(K["SYMBOLS"])) if avg_chart else None, "log": tail,
    }).encode()


def kronos_smc(sym: str, tf: str, since_ms: int) -> bytes:
    """The /kronos chart's SMC overlay: David's BOS / CHoCH and his S&D zones on this timeframe (smc_compare.page, the same
    numbers as /smc), only what reaches the chart's first bar."""
    from . import smc_compare
    d = smc_compare.page(sym, tf)
    if "error" in d:
        return json.dumps({"error": d["error"]}).encode()
    M = d["major"]
    keep = ("side", "top", "bottom", "mid", "proximal", "distal", "bos_level", "t_break", "t0", "t_c", "fvg", "targets",
            "status", "live", "t_touch", "t_end", "fib_ext")
    sdd = [{k: z.get(k) for k in keep} for z in d.get("sdd", [])
           if z.get("valid") and (z.get("live") or (z.get("t_end") or 0) >= since_ms)]
    return json.dumps({"sym": sym, "tf": tf, "trend": M.get("trend"), "protected": M.get("protected"), "bos_level": M.get("bos_level"),
                       "breaks": [b for b in M["breaks"] if b["t"] >= since_ms], "sdd": sdd}).encode()


_JR = [None, []]    # journal.jsonl parsed once per size change


def _journal() -> list:
    path = os.path.join(DATA_DIR, "journal.jsonl")
    try:
        sz = os.path.getsize(path)
    except OSError:
        return []
    if _JR[0] != sz:
        rows = []
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
        _JR[0], _JR[1] = sz, rows
    return _JR[1]


def _iso_ms(at: str) -> int:
    import datetime as dt
    return int(dt.datetime.fromisoformat(at).timestamp() * 1000)


def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ── a strategy's room (David 2026-11-12: "above the room show the version ... and controls for that") ──
# the files that ARE the strategy: its version = how many commits changed them, the latest one first
ROOMS = {
    "V5 engine": {"files": ["engine/strategy.py", "engine/book.py", "engine/filters.py"], "config": "STRATEGY", "control": None},
    "S&D David": {"files": ["engine/sdd_book.py", "engine/sd_david.py"], "config": "SDD", "control": "sdd"},
    "Kronos": {"files": ["engine/kronos_book.py", "concepter/kronos/signals.py"], "config": "KRONOS", "control": "kronos"},
    "Claude": {"files": ["engine/tools/claude_crypto.py", "engine/tools/claude_kscalp.py", "engine/tools/claude_night.sh"],
               "config": None, "control": None},
    "Fib trend": {"files": ["engine/fib_book.py", "engine/fib_trend.py"], "config": "FIB", "control": "fib"},
    "S&D layers": {"files": ["engine/sdd_layers.py"], "config": "SDD_LAYERS", "control": "sdd_layers"},
}
_ROOM_GIT: Dict = {}


def room_info(name: str) -> bytes:
    import subprocess
    import time as _t
    from . import config as CF
    r = ROOMS.get(name)
    if r is None:
        return json.dumps({"name": name, "known": False}).encode()
    root = os.path.dirname(HERE)
    hit = _ROOM_GIT.get(name)
    if not hit or _t.time() - hit[0] > 120:
        try:
            out = subprocess.run(["git", "-C", root, "log", "--format=%h%x09%cI%x09%s", "--", *r["files"]],
                                 capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
        except Exception:
            out = []
        hist = [dict(zip(("commit", "date", "subject"), x.split("\t", 2))) for x in out if x.count("\t") >= 2]
        _ROOM_GIT[name] = hit = (_t.time(), hist)
    hist = hit[1]
    ctl = CF.load_control()
    cfg = getattr(CF, r["config"], None) if r["config"] else None
    settings = {k: v for k, v in (cfg or {}).items()
                if isinstance(v, (int, float, bool, str)) and k not in ("DIR",) and len(str(v)) <= 60}
    on = None
    if r["control"]:
        on = bool(ctl.get(r["control"], (cfg or {}).get("ENABLED", False)))
    return json.dumps({"name": name, "known": True, "version": len(hist), "latest": hist[0] if hist else None,
                       "history": hist[:8], "files": r["files"], "control": r["control"], "on": on,
                       "trading": bool(ctl.get("trading")), "settings": settings}).encode()


def sdd_compare() -> bytes:
    """S&D David (one entry at A's wick, all out at T1) vs S&D layers (3 entries, 3 targets) on the SAME zones, zone by
    zone (David 2026-11-12: "track this vs now normal tp how this differ"). Only zones the layered book saw count: from
    the day it went live. A zone is 'done' when neither side has anything waiting or open."""
    nrm = (_read_json(SDD_STATE).get("orders") or {})
    lay = (_read_json(os.path.join(DATA_DIR, "sdd_layers", "state.json")).get("orders") or {})
    by: Dict[str, list] = {}
    for o in lay.values():
        by.setdefault(o["zone_id"], []).append(o)
    rows = []
    for zid, Ls in by.items():
        n = nrm.get(zid)
        Ls = sorted(Ls, key=lambda x: x["layer"])
        live = lambda st: st in ("pending", "open")
        real = [x for x in Ls if x["state"] not in ("skipped",)]
        if not real and not n:
            continue
        r = {"zone_id": zid, "symbol": Ls[0]["symbol"], "side": Ls[0]["side"], "placed_ms": min(x.get("placed_ms") or 0 for x in Ls),
             "normal": None if not n else {"state": n.get("state"), "pnl": n.get("pnl_usd"), "pnl_now": n.get("pnl_now"),
                                            "end": n.get("end"), "entry": n.get("entry"), "price": n.get("price"), "tp": n.get("tp")},
             "layers": [{"k": x["layer"], "state": x["state"], "pnl": x.get("pnl_usd"), "pnl_now": x.get("pnl_now"), "end": x.get("end"),
                         "price": x.get("price"), "tp": x.get("tp")} for x in Ls]}
        r["layers_pnl"] = round(sum(x.get("pnl_usd") or 0 for x in Ls if x["state"] == "closed"), 2)
        r["layers_float"] = round(sum(x.get("pnl_now") or 0 for x in Ls if x["state"] == "open"), 2)
        r["layers_filled"] = sum(1 for x in Ls if x["state"] in ("open", "closed"))
        r["normal_pnl"] = (n or {}).get("pnl_usd") if (n or {}).get("state") == "closed" else (0.0 if n and n.get("state") == "cancelled" else None)
        r["done"] = not any(live(x["state"]) for x in Ls) and not (n and live(n.get("state")))
        rows.append(r)
    rows.sort(key=lambda r: r["placed_ms"], reverse=True)
    D = [r for r in rows if r["done"]]
    tot = {"zones": len(rows), "done": len(D),
           "normal_pnl": round(sum(r["normal_pnl"] or 0 for r in D), 2), "layers_pnl": round(sum(r["layers_pnl"] for r in D), 2),
           "normal_traded": sum(1 for r in D if r["normal"] and r["normal"]["state"] == "closed"),
           "layers_traded": sum(1 for r in D if r["layers_filled"]),
           "layers_better": sum(1 for r in D if r["layers_pnl"] > (r["normal_pnl"] or 0) + 1e-9),
           "normal_better": sum(1 for r in D if (r["normal_pnl"] or 0) > r["layers_pnl"] + 1e-9),
           "normal_open_pnl": round(sum(((r["normal"] or {}).get("pnl_now") or 0) for r in rows
                                        if not r["done"] and (r["normal"] or {}).get("state") == "open"), 2),
           "layers_open_pnl": round(sum(r["layers_float"] for r in rows if not r["done"]), 2)}
    return json.dumps({"totals": tot, "zones": rows[:300]}).encode()


def trades_all() -> bytes:
    d = _trade_rows()
    for k in ("open", "closed", "waiting"):        # the checklist + chart marks go out per trade (/api/trade/why)
        for r in d[k]:
            m = r.get("meta") or {}
            r["meta"] = {x: v for x, v in m.items() if x not in ("checks", "marks")}
            r["has_checks"] = bool(m.get("checks"))
    return json.dumps(d).encode()


def trade_why(tid: str) -> bytes:
    """One trade's checklist: what the strategy checked before the entry, the value it saw, the rule, and the chart
    marks it used (engine/trade_checks.py; recorded at the entry, or rebuilt from the candles for older trades)."""
    from .trade_checks import explain
    d = _trade_rows()
    row = next((r for k in ("open", "waiting", "closed") for r in d[k] if r["id"] == tid), None)
    if row is None:
        return json.dumps({"error": "no such trade"}).encode()
    return json.dumps({"id": tid, **explain(row)}).encode()


def _trade_rows() -> Dict:
    """The home page's trade lists: every strategy that trades the account (V5 engine, S&D David, Kronos, Claude), open and
    closed, one row shape: strategy, symbol, side, entry / SL / TP, times, exit, P&L and the 'why' + the zone that drew it.
    All from the files the engine already writes (the dashboard never talks to MT5)."""
    now_ms = int(__import__("time").time() * 1000)
    opens, closed, waiting = [], [], []

    def row(strategy, t, **kw):
        r = {"strategy": strategy, "symbol": t.get("symbol"), "side": t.get("side"), "lots": t.get("lots"),
             "entry": t.get("entry"), "sl": t.get("sl"), "tp": t.get("tp")}
        r.update(kw)
        return r

    kv = _read_json(os.path.join(KRONOS_DIR, "view.json"))
    done_k = set()
    for t in kv.get("closed", []):
        done_k.add(t["id"])
        closed.append(row("Kronos", t, id="K" + t["id"], opened_ms=t.get("opened_ms"), closed_ms=t.get("closed_ms"), exit=t.get("exit"),
                          pnl=t.get("pnl_usd"), reason=t.get("reason"), ticket=t.get("ticket"),
                          why=f"Kronos P up {round((t.get('p_up') or 0) * 100)} %, median in 2 h {t.get('median_end')}",
                          meta={"p_up": t.get("p_up"), "median_end": t.get("median_end"), "bar_t": t.get("bar_t"),
                                "checks": t.get("checks"), "marks": t.get("marks")}))
    ent = {}
    for e in _journal():
        if e.get("event") == "kronos_entry":
            ent[e["id"]] = e
    for e in _journal():                                   # the Kronos trades older than the 50 the page keeps
        if e.get("event") == "kronos_exit" and e["id"] in ent and e["id"] not in done_k:
            a = ent[e["id"]]
            closed.append(row("Kronos", a, id="K" + e["id"], opened_ms=_iso_ms(a["at"]), closed_ms=_iso_ms(e["at"]), exit=e.get("exit"),
                              pnl=e.get("pnl_usd"), reason=e.get("reason"),
                              why=f"Kronos P up {round((a.get('p_up') or 0) * 100)} %", meta={"p_up": a.get("p_up")}))
    for t in kv.get("open", []):
        opens.append(row("Kronos", t, id="K" + t["id"], opened_ms=t.get("opened_ms"), now=t.get("price_now"), pnl=t.get("pnl_now"),
                         ticket=t.get("ticket"), close_by_ms=t.get("close_by_ms"),
                         why=f"Kronos P up {round((t.get('p_up') or 0) * 100)} %, median in 2 h {t.get('median_end')}",
                         meta={"p_up": t.get("p_up"), "median_end": t.get("median_end"), "bar_t": t.get("bar_t"),
                               "checks": t.get("checks"), "marks": t.get("marks")}))
    cl = kv.get("claude") or {}
    for t in cl.get("closed", []):
        closed.append(row("Claude", t, id="C" + str(t["id"]), opened_ms=t.get("opened_ms"), closed_ms=t.get("closed_ms"), exit=t.get("exit"),
                          pnl=t.get("pnl_usd"), reason=t.get("reason"), ticket=t.get("ticket"), why=t.get("why"),
                          meta={"plan": t.get("plan"), "rule": t.get("rule"), "rule_tf": t.get("rule_tf"),
                                "checks": t.get("checks"), "marks": t.get("marks")}))
    for t in cl.get("open", []):
        opens.append(row("Claude", t, id="C" + str(t["id"]), opened_ms=t.get("opened_ms"), now=t.get("price_now"), pnl=t.get("pnl_now"),
                         ticket=t.get("ticket"), why=t.get("why"), meta={"plan": t.get("plan"), "rule": t.get("rule"),
                                                                          "rule_tf": t.get("rule_tf"), "checks": t.get("checks"),
                                                                          "marks": t.get("marks")}))
    sd = _read_json(os.path.join(DATA_DIR, "sdd", "state.json"))
    fills = {e["id"]: _iso_ms(e["at"]) for e in _journal() if e.get("event") == "sdd_fill"}
    for o in (sd.get("orders") or {}).values():
        meta = {"zone": o.get("zone"), "zone_top": o.get("zone_top"), "zone_bottom": o.get("zone_bottom"), "t_a": o.get("t_a"),
                "t_break": o.get("t_break"), "rr": o.get("rr"), "risk_usd": o.get("risk_usd"),
                "checks": o.get("checks"), "marks": o.get("marks")}
        base = row("S&D David", {**o, "entry": o.get("entry", o.get("price"))}, id="S" + o["id"], ticket=o.get("ticket"), meta=meta,
                   why=f"S&D David {o.get('zone')} zone (candle A), limit at the wick, stop beyond A, T1")
        st = o.get("state")
        if st == "closed":
            closed.append({**base, "opened_ms": o.get("opened_ms") or fills.get(o["id"]) or o.get("placed_ms"), "closed_ms": o.get("ended_ms"), "exit": o.get("exit"),
                           "pnl": o.get("pnl_usd"), "reason": o.get("end")})
        elif st == "pending":
            waiting.append({**base, "entry": o.get("price"), "placed_ms": o.get("placed_ms")})
        elif st != "cancelled" and o.get("opened_ms"):
            opens.append({**base, "opened_ms": o.get("opened_ms"), "now": o.get("price_now"), "pnl": o.get("pnl_now")})
    sl = _read_json(os.path.join(DATA_DIR, "sdd_layers", "state.json"))       # S&D David with layer entries (sdd_layers.py)
    for o in (sl.get("orders") or {}).values():
        st = o.get("state")
        if st in ("skipped", "cancelled"):
            continue
        meta = {"zone": o.get("zone"), "zone_top": o.get("zone_top"), "zone_bottom": o.get("zone_bottom"), "t_a": o.get("t_a"),
                "t_break": o.get("t_break"), "rr": o.get("rr"), "risk_usd": o.get("risk_usd"), "layer": o.get("layer"),
                "zone_id": o.get("zone_id"), "checks": o.get("checks"), "marks": o.get("marks")}
        base = row("S&D layers", {**o, "entry": o.get("entry", o.get("price"))}, id="Y" + o["id"], ticket=o.get("ticket"), meta=meta,
                   why=f"S&D layer L{o.get('layer')} ({o.get('where')}) of zone {o.get('zone_id')}, one stop beyond A, TP{o.get('layer')}")
        if st == "closed":
            closed.append({**base, "opened_ms": o.get("opened_ms") or o.get("placed_ms"), "closed_ms": o.get("ended_ms"),
                           "exit": o.get("exit"), "pnl": o.get("pnl_usd"), "reason": o.get("end")})
        elif st == "pending":
            waiting.append({**base, "entry": o.get("price"), "placed_ms": o.get("placed_ms")})
        elif st == "open":
            opens.append({**base, "opened_ms": o.get("opened_ms"), "now": o.get("price_now"), "pnl": o.get("pnl_now")})
    ov = _read_json(os.path.join(DATA_DIR, "overview.json"))
    pos = {p.get("ticket"): p for p in ov.get("positions", [])}
    for t in ov.get("trades", []):                          # V5 engine, open
        ps = [pos[x["ticket"]] for x in (t.get("normal"), t.get("layer")) if x and x.get("ticket") in pos]
        opens.append(row("V5 engine", {**t, "sl": t.get("stop"), "lots": (t.get("normal") or {}).get("lots")}, id="V" + t["id"],
                         opened_ms=t.get("opened_ms"), now=ps[0].get("price_current") if ps else None,
                         pnl=sum(p.get("profit") or 0 for p in ps), tp1=t.get("tp1"),
                         why=f"V5 {t.get('tf')} {t.get('mode')} · {t.get('tp_label')}", meta={"rr": t.get("rr"), "tf": t.get("tf")}))
    for t in (_read_json(os.path.join(DATA_DIR, "state.json")).get("trades") or {}).values():
        if t.get("closed"):
            closed.append(row("V5 engine", {**t, "sl": t.get("stop0"), "lots": (t.get("normal") or {}).get("lots")}, id="V" + t["id"],
                              opened_ms=t.get("opened_ms"), closed_ms=None, pnl=t.get("pnl_usd"), tp1=t.get("tp1"),
                              reason="closed", why=f"V5 {t.get('tf')} {t.get('mode')} · {t.get('tp_label')}",
                              meta={"rr": t.get("rr"), "tf": t.get("tf")}))
    closed.sort(key=lambda r: r.get("closed_ms") or r.get("opened_ms") or 0, reverse=True)
    opens.sort(key=lambda r: r.get("opened_ms") or 0, reverse=True)
    waiting.sort(key=lambda r: r.get("placed_ms") or 0, reverse=True)
    names = ["V5 engine", "S&D David", "S&D layers", "Kronos", "Claude"]
    tot = {n: {"open": sum(r["strategy"] == n for r in opens), "closed": sum(r["strategy"] == n for r in closed),
               "waiting": sum(r["strategy"] == n for r in waiting),
               "won": sum(r["strategy"] == n and (r.get("pnl") or 0) > 0 for r in closed),
               "pnl": round(sum((r.get("pnl") or 0) for r in closed if r["strategy"] == n), 2),
               "float": round(sum((r.get("pnl") or 0) for r in opens if r["strategy"] == n), 2)} for n in names}
    return {"now": now_ms, "open": opens, "closed": closed, "waiting": waiting, "totals": tot}


def _kronos_past(sym: str, lo_ms: int, hi_ms: int) -> list:
    """Every Kronos forecast of this symbol made between lo and hi (signals.jsonl): [bar_t, last, median, q10, q90]."""
    out = {}
    try:
        with open(os.path.join(KRONOS_DIR, "signals.jsonl"), "rb") as f:
            key = f'"symbol": "{sym}"'.encode()
            for line in f:
                if key not in line:
                    continue
                try:
                    h = json.loads(line)
                except ValueError:
                    continue
                if lo_ms <= h.get("bar_t", 0) <= hi_ms and h.get("median"):
                    out[h["bar_t"]] = [h["bar_t"], h.get("last"), h["median"], h.get("q10"), h.get("q90")]
    except OSError:
        pass
    return [out[k] for k in sorted(out)]


def trade_bars(sym: str, t0_ms: int, t1_ms: int, tf: str = "M15", kronos: bool = False) -> bytes:
    """M15 candles around one trade for the detail chart: saved history (deep) + the Kronos feed + the view bars, merged by time."""
    ms = TF_MS[tf]
    merged = {}
    try:
        path = os.path.join(DATA_DIR, "history", f"{sym}.json")
        mt = os.path.getmtime(path)
        if _HIST.get((sym, "T" + tf), (0,))[0] != mt:
            with open(path) as f:
                _HIST[(sym, "T" + tf)] = (mt, json.load(f)["bars"].get(tf, [])[-8000:])
        for b in _HIST[(sym, "T" + tf)][1]:
            merged[b[0]] = [b[0], b[1], b[2], b[3], b[4]]
    except (OSError, ValueError, KeyError):
        pass
    if tf == "M15":
        for r in _read_json(os.path.join(KRONOS_DIR, "feed", f"{sym}.json")).get("bars", []):
            merged[r[0]] = [r[0], r[1], r[2], r[3], r[4]]
    for r in (_read_json(os.path.join(VIEW_DIR, f"{sym}.json")).get("bars") or {}).get(tf, []):
        merged[r[0] * 1000] = [r[0] * 1000, r[1], r[2], r[3], r[4]]
    lo, hi = t0_ms - 70 * ms, t1_ms + 30 * ms
    bars = [[b[0] // 1000] + b[1:] for t, b in sorted(merged.items()) if lo <= t <= hi][-700:]
    res = {"symbol": sym, "tf": tf, "bars": bars}
    if kronos and bars:                                   # every earlier Kronos forecast on the candles shown
        res["kronos"] = _kronos_past(sym, bars[0][0] * 1000 - 8 * 900_000, bars[-1][0] * 1000)
    return json.dumps(res).encode()


def backtest_summary() -> bytes:
    """Every report*.json (one per backtest run) + the chart index, for the Backtest page."""
    out = {"runs": {}, "charts": [], "variants": None}
    try:
        names = sorted(f for f in os.listdir(BT_DIR) if f.startswith("report") and f.endswith(".json"))
    except FileNotFoundError:
        names = []
    for f in names:
        with open(os.path.join(BT_DIR, f)) as fh:
            out["runs"][f[len("report"):-5].lstrip("_") or "main"] = json.load(fh)
    for key, f in (("charts", "charts/index.json"), ("variants", "variants.json")):
        try:
            with open(os.path.join(BT_DIR, f)) as fh:
                out[key] = json.load(fh)
        except FileNotFoundError:
            pass
    return json.dumps(out).encode()


class Handler(BaseHTTPRequestHandler):
    public = False

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: str):
        try:
            with open(path, "rb") as f:
                return self._send(200, f.read())
        except FileNotFoundError:
            return self._send(404, b'{"error":"not yet written"}')

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/desk"):        # David 2026-11-12: "/" = the office floor (office.html), the old home page = /desk
            with open(os.path.join(HERE, "office.html" if u.path == "/" else "dashboard.html"), "rb") as f:
                html = f.read()
            if self.public:
                html = html.replace(b"</head>", PUBLIC_CSS + b"</head>", 1)
            return self._send(200, html, "text/html; charset=utf-8")
        if u.path == "/room":                # one strategy's room: version + controls, then every trade as a chart
            with open(os.path.join(HERE, "room.html"), "rb") as f:
                html = f.read()
            if self.public:
                html = html.replace(b"</head>", PUBLIC_CSS + b"</head>", 1)
            return self._send(200, html, "text/html; charset=utf-8")
        if u.path == "/api/sdd/compare":
            return self._send(200, sdd_compare())
        if u.path == "/api/room":
            return self._send(200, room_info(q.get("s", "")))
        if u.path == "/api/overview":
            if not self.public:
                return self._file(OVERVIEW_FILE)
            try:
                with open(OVERVIEW_FILE) as f:
                    ov = json.load(f)
            except FileNotFoundError:
                return self._send(404, b'{"error":"not yet written"}')
            for k in ("account", "mt5"):
                if isinstance(ov.get(k), dict):
                    ov[k].pop("login", None)
            return self._send(200, json.dumps(ov).encode())
        if u.path == "/kronos":
            with open(os.path.join(HERE, "kronos.html"), "rb") as f:
                html = f.read()
            if self.public:
                html = html.replace(b"</head>", PUBLIC_KRONOS_CSS + b"</head>", 1)
            return self._send(200, html, "text/html; charset=utf-8")
        if u.path == "/api/status":
            # file-only (state / view / overview / pnl): the dashboard never touches MT5
            from .status import build as _status
            sym = q.get("sym", "")
            if sym and not SYM.match(sym):
                return self._send(400, b'{"error":"bad symbol"}')
            try:
                return self._send(200, json.dumps(_status(sym)).encode())
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}).encode())
        if u.path == "/api/pnl":
            return self._file(PNL_FILE)
        if u.path == "/api/sdd":
            return self._file(SDD_STATE)
        if u.path == "/api/fib":
            return self._file(FIB_STATE)
        if u.path == "/api/fib/backtest":
            return self._file(FIB_BT)
        if u.path == "/api/kronos/smc":
            sym, tf = q.get("sym", ""), q.get("tf", "M15")
            if not SYM.match(sym) or tf not in TF_MS or not q.get("since", "0").isdigit():
                return self._send(400, b'{"error":"bad request"}')
            try:
                return self._send(200, kronos_smc(sym, tf, int(q.get("since", "0"))))
            except Exception as e:                       # the overlay is optional: the chart still draws
                return self._send(200, json.dumps({"error": str(e)[:200]}).encode())
        if u.path == "/api/trades":
            return self._send(200, trades_all())
        if u.path == "/api/trade/why":
            return self._send(200, trade_why(q.get("id", "")))
        if u.path == "/api/trade/bars":
            sym, tf = q.get("sym", ""), q.get("tf", "M15")
            if not SYM.match(sym) or tf not in TF_MS or not q.get("from", "0").isdigit() or not q.get("to", "0").isdigit():
                return self._send(400, b'{"error":"bad request"}')
            return self._send(200, trade_bars(sym, int(q["from"]), int(q["to"]), tf, q.get("kronos") == "1"))
        if u.path == "/api/kronos/status":
            return self._send(200, kronos_status())
        if u.path == "/api/kronos":
            return self._file(KRONOS_VIEW)
        # Kronos × S&D David zones: will price touch the fresh zone in the next 50 M15 candles (concepter/kronos/zone_touch.py)
        if u.path == "/kzones":
            with open(os.path.join(HERE, "kzones.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/kzones":
            return self._file(os.path.join(KRONOS_DIR, "zones", "zones.json"))
        if u.path == "/api/kzones/backtest":            # concepter/kronos/zone_backtest.py: the same test on past candles
            return self._file(os.path.join(KRONOS_DIR, "zones", "backtest.json"))
        if u.path == "/api/kronos/chart":
            sym = q.get("sym", "")
            if not SYM.match(sym):
                return self._send(400, b'{"error":"bad symbol"}')
            try:
                tf = q.get("tf", "M15")
                if tf not in TF_MS:
                    return self._send(400, b'{"error":"bad timeframe"}')
                return self._send(200, kronos_chart(sym, tf))
            except FileNotFoundError:
                return self._send(404, b'{"error":"no bars yet"}')
        if u.path == "/backtest":
            with open(os.path.join(HERE, "backtest.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/backtest":
            return self._send(200, backtest_summary())
        if u.path == "/bt/chart":
            sid = q.get("id", "")
            if not SETUP_ID.match(sid):
                return self._send(400, b'{"error":"bad id"}')
            try:
                with open(os.path.join(BT_DIR, "charts", f"{sid}.png"), "rb") as f:
                    return self._send(200, f.read(), "image/png")
            except FileNotFoundError:
                return self._send(404, b'{"error":"no chart"}')
        if u.path == "/api/view":
            sym = q.get("sym", "")
            if not SYM.match(sym):
                return self._send(400, b'{"error":"bad symbol"}')
            return self._file(os.path.join(VIEW_DIR, f"{sym}.json"))
        # free SMC indicators (SMC Zones, LuxAlgo) next to the V5 engine, computed here from the bar files (2026-10-28)
        if u.path == "/smc":
            with open(os.path.join(HERE, "smc.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/smc/list":
            from . import smc_compare
            return self._send(200, json.dumps(smc_compare.available()).encode())
        if u.path == "/api/smc":
            from . import learn, smc_compare
            sym, tf = q.get("sym", ""), q.get("tf", "")
            if not SYM.match(sym) or tf not in learn.TF_MS:
                return self._send(400, b'{"error":"bad symbol / tf"}')
            want = q.get("bars", "")
            n = smc_compare.FULL_BARS if want == "all" else (max(500, min(smc_compare.FULL_BARS, int(want)))
                                                             if want.isdigit() else smc_compare.N_BARS)
            return self._send(200, json.dumps(smc_compare.page(sym, tf, n)).encode())
        if u.path == "/api/smc/orderflow":     # the footprint chart (orderflow.py); since = only the bars from that time on
            from . import learn, orderflow
            sym, tf = q.get("sym", ""), q.get("tf", "")
            if not SYM.match(sym) or tf not in learn.TF_MS:
                return self._send(400, b'{"error":"bad symbol / tf"}')
            d = orderflow.page(sym, tf)
            since = q.get("since", "")
            if since.isdigit() and "t" in d:
                k = bisect.bisect_left(d["t"], int(since))
                d = {**d, "t": d["t"][k:], "bars": d["bars"][k:], "cvd": d["cvd"][k:], "since": int(since)}
            return self._send(200, json.dumps(d).encode())
        if u.path == "/api/smc/live":          # the tick + forming bars, read by the engine while a page asks (live.py)
            from . import live, smc_compare
            sym = q.get("sym", "")
            if not SYM.match(sym) or sym not in smc_compare.available():     # only real symbols get a want file
                return self._send(400, b'{"error":"bad symbol"}')
            live.want(sym)
            return self._send(200, json.dumps(live.read(sym)).encode())
        # the learning chart (David 2026-10-25); on the public copy too — David and his friend draw there,
        # but only with the secret key in the link; without it the page is view-only
        if u.path.startswith("/learn") or u.path.startswith("/api/learn/"):
            if u.path == "/learn":
                with open(os.path.join(HERE, "learn.html"), "rb") as f:
                    html = f.read()
                if self.public and q.get("key") != learn_key():
                    html = html.replace(b"</head>", PUBLIC_LEARN_CSS + b"</head>", 1)
                return self._send(200, html, "text/html; charset=utf-8")
            from . import learn
            sym, tf = q.get("sym", ""), q.get("tf", "")
            if u.path == "/api/learn/labels":
                return self._send(200, json.dumps(learn.labels(sym or None, tf or None)).encode())
            if u.path == "/api/learn/compare":
                return self._send(200, json.dumps(learn.compare(sym or None, tf or None)).encode())
            if u.path in ("/api/learn/bars", "/api/learn/detect"):
                if not SYM.match(sym) or tf not in learn.TF_MS:
                    return self._send(400, b'{"error":"bad symbol / tf"}')
                n = max(200, min(6000, int(q.get("n") or 3000)))
                body = learn.load_bars(sym, tf, n) if u.path.endswith("bars") else learn.detect(sym, tf, n)
                return self._send(200, json.dumps(body).encode())
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/cmd", "/api/learn/label") or self.headers.get("X-V5") != "1" \
                or (self.public and path != "/api/learn/label"):
            return self._send(403, b'{"error":"forbidden"}')
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            c = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, b'{"error":"bad json"}')
        if path == "/api/learn/label":
            from . import learn
            if self.public and str(c.get("key", "")) != learn_key():
                return self._send(403, b'{"error":"drawing on the internet copy needs the secret link"}')
            by = "public" if self.public else None
            try:
                if c.get("op") == "del":
                    learn.delete_label(c.get("id", ""), by)
                    return self._send(200, b'{"deleted":true}')
                if c.get("op") == "note":
                    learn.note_label(c.get("id", ""), c.get("note", ""), by)
                    return self._send(200, b'{"noted":true}')
                return self._send(200, json.dumps({"saved": learn.save_label(c, by)}).encode())
            except ValueError as e:
                return self._send(400, json.dumps({"error": str(e)}).encode())
        if c.get("action") not in ACTIONS:
            return self._send(400, b'{"error":"unknown action"}')
        clean = {"action": c["action"]}
        if c["action"] in ("trading", "kronos", "sdd", "fib", "sdd_layers"):
            clean["on"] = bool(c.get("on"))
        elif c["action"] == "mt5":
            if c.get("op") not in MT5_OPS:
                return self._send(400, b'{"error":"unknown mt5 op"}')
            clean["op"] = c["op"]
        elif c["action"] in ("cancel_setup", "close_setup"):
            clean["id"] = str(c.get("id", ""))[:80]
        else:
            try:
                clean["ticket"] = int(c.get("ticket"))
            except (TypeError, ValueError):
                return self._send(400, b'{"error":"bad ticket"}')
        with open(COMMANDS_FILE, "a") as f:
            f.write(json.dumps(clean) + "\n")
        self._send(200, json.dumps({"queued": clean}).encode())

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser(description="V5 chart dashboard (read-only files + queued controls)")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--public", action="store_true", help="view only: no controls, POSTs refused, login hidden")
    a = ap.parse_args()
    Handler.public = a.public
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"V5 dashboard{' (public, view only)' if a.public else ''} on http://127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
