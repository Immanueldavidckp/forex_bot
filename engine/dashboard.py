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

ACTIONS = {"trading", "cancel_setup", "close_setup", "close_ticket", "mt5", "kronos", "kronos_close"}
KRONOS_DIR = os.path.join(DATA_DIR, "kronos")
KRONOS_VIEW = os.path.join(KRONOS_DIR, "view.json")              # engine/kronos_book.py → the /kronos page
MT5_OPS = {"start", "stop", "restart", "login"}
SYM = re.compile(r"^[A-Za-z0-9._#-]{1,24}$")
SETUP_ID = re.compile(r"^[A-Za-z0-9._#-]{1,24}-(M5|M15|M30|H1|H4)-[DS]-\d{6,12}$")
# --public: the control buttons are hidden (the server refuses the POSTs anyway)
PUBLIC_CSS = (b"<style>#trading,#mt5-restart,#mt5-stop,#mt5-start,[data-close],[data-ticket],[data-cancel],"
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


def kronos_chart(sym: str) -> bytes:
    """The /kronos big chart: every bar Kronos read (feed/<SYM>.json), its latest forecast with each path, and the
    symbol's last 80 forecasts (the tail of signals.jsonl) to lay over the candles they forecast."""
    with open(os.path.join(KRONOS_DIR, "feed", f"{sym}.json")) as f:
        bars = [[r[0] // 1000, r[1], r[2], r[3], r[4]] for r in json.load(f)["bars"]]
    try:
        with open(os.path.join(KRONOS_DIR, "signals.json")) as f:
            sig = json.load(f).get(sym)
    except (FileNotFoundError, ValueError):
        sig = None
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
    return json.dumps({"symbol": sym, "bars": bars, "signal": sig, "history": hist[::-1]}).encode()


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
        if u.path == "/":
            with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                html = f.read()
            if self.public:
                html = html.replace(b"</head>", PUBLIC_CSS + b"</head>", 1)
            return self._send(200, html, "text/html; charset=utf-8")
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
        if u.path == "/api/kronos":
            return self._file(KRONOS_VIEW)
        if u.path == "/api/kronos/chart":
            sym = q.get("sym", "")
            if not SYM.match(sym):
                return self._send(400, b'{"error":"bad symbol"}')
            try:
                return self._send(200, kronos_chart(sym))
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
        if c["action"] in ("trading", "kronos"):
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
