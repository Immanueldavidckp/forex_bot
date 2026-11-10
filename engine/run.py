"""
engine/run.py — the V5 engine's loop and commands. Run from ~/forex with the system python3:

    python3 -m engine.run check        account, symbols, clock, one analysis pass (no orders)
    python3 -m engine.run once         one analysis pass: writes the dashboard files, prints the setups
    python3 -m engine.run run          the loop (watch mode until trading is switched on in the dashboard)
    python3 -m engine.run trading on|off
    python3 -m engine.run mt5 status|start|stop|restart|login      the MT5 terminal (the loop runs it: engine/terminal.py)
    python3 -m engine.run filters on|off|status      the structure filter layer (engine/filters.py), no restart needed
    python3 -m engine.run filters strict|test|profit its thresholds: the spec as written, the 0.01-lot test
                                                    profile, or "profit" (no caps + the cost gate, David 2026-10-30)
    python3 -m engine.run kronos on|off|status       Kronos' trades (engine/kronos_book.py; forecasts: service kronos-signals)
    python3 -m engine.run sdd on|off|status          DAVID's S&D zones traded on M15 (engine/sdd_book.py)

Every loop_sec: read the account / positions / pending layers, apply the dashboard's commands, manage
the open trades. Every time a timeframe is due (M5 / M15 each minute, M30 / H1 every 5 min, H4 every
15 min): re-read it for every symbol, and after each M5 read run the picker on every symbol. Orders go
out only when trading is on (control.json), the account is a demo and the terminal's Algo Trading is on.
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback

from .book import Book, journal, log
from .config import ENGINE, STRATEGY, load_control, save_control
from . import filters as FL
from .feed import Feed, mt5c
from .kronos_book import KronosBook
from . import live as LV
from . import kronos_book as KB
from .sdd_book import SddBook
from . import sdd_book as SB
from .terminal import Terminal


def _ready(book: Book) -> str:
    a = book.account
    if ENGINE.get("mt5_login") and a.get("login") != ENGINE["mt5_login"]:
        return f"the terminal is on {a.get('server')} {a.get('login')}, not the engine's {ENGINE['mt5_login']}: trading stays off"
    if ENGINE["demo_only"] and not a.get("demo"):
        return f"{a.get('server')} {a.get('login')} is NOT a demo account: trading stays off"
    if not a.get("algo_trading"):
        return "Algo Trading is off in the terminal (Ctrl+E): orders would be refused"
    return ""


def _utc(off) -> str:
    return f"UTC{'+' if off and off.total_seconds() >= 0 else ''}{off.total_seconds() / 3600 if off is not None else 'n/a (NY+7 rule)'}"


def start(analyse: bool = True) -> Book:
    feed = Feed()
    syms = feed.discover()
    off = feed.detect_clock()
    log(f"{len(syms)} symbols ({sum(1 for s in syms if feed.market[s] == 'crypto')} crypto, "
        f"{sum(1 for s in syms if feed.market[s] == 'forex')} forex), server clock {_utc(off)}")
    t0 = time.time()
    feed.refresh(force=True)
    log(f"bars: {len(feed.bars)} series in {time.time() - t0:.0f} s")
    book = Book(feed)
    book.read_broker()
    if analyse:
        for s in syms:
            try:
                book.analyse(s, trading=False)
            except Exception as e:
                log(f"{s}: analysis error {type(e).__name__}: {e}")
    return book


def cmd_check(a) -> int:
    book = start()
    acct = book.account
    print(f"account   {acct.get('server')} {acct.get('login')}  demo={acct.get('demo')}  equity {acct.get('equity')}  "
          f"Algo Trading={'on' if acct.get('algo_trading') else 'OFF'}")
    print(f"positions {book.running()} open, {book.pending_layers()} pending layers (this engine's magic {book.magic})")
    print(f"trading   {'ON' if load_control()['trading'] else 'off (watch mode)'}{'; ' + _ready(book) if _ready(book) else ''}")
    for s in book.feed.symbols:
        v = book.views.get(s)
        if not v:
            print(f"  {s:12s} not enough bars")
            continue
        live = [x for x in v["setups"] if x["status"] == "waiting pullback" and x.get("aligned")]
        f = next((x for x in live if x["id"] == v["focus"]), None)
        print(f"  {s:12s} bias {str(v['bias']['bias']):5s} trend " + " ".join(f"{tf}:{(v['trend'].get(tf) or '-')[:4]}" for tf in v["trend"])
              + f" | {len(live)} live aligned setup(s)"
              + (f": {f['tf']} {f['kind']} BOS {f['bos']['level']:g}, FVG {f['fvg_pick']}/{len(f['fvgs'])}, entry {f['entry']:g}" if f else ""))
    book.overview(load_control()["trading"])
    book.save()
    return 0


def cmd_once(a) -> int:
    return cmd_check(a)


def cmd_trading(a) -> int:
    c = save_control(trading=a.state == "on")
    journal("trading", on=c["trading"], by="cli")
    print(f"trading {'ON' if c['trading'] else 'off'} (the running engine picks it up within {ENGINE['loop_sec']} s)")
    return 0


def _mt5_error(e: Exception) -> bool:
    m = str(e)
    return isinstance(e, mt5c.Mt5Error) or "initialize failed" in m or "IPC" in m or "terminal" in m.lower()


def cmd_run(a) -> int:
    term = Terminal(log, journal)                 # the engine runs the MT5 terminal (engine/terminal.py)
    book = None
    while book is None:
        try:
            if term.ensure_running():
                book = start(analyse=False)
                continue
            log(f"MT5 not available ({term.status['mode']}: {term.status.get('waiting') or term.status.get('last_error')}), waiting")
        except Exception as e:
            log(f"start failed: {type(e).__name__}: {e}")
            if _mt5_error(e):
                term.on_error(e)
        time.sleep(30)
    feed = book.feed
    log(f"engine running: magic {book.magic}, max {book.max_slots()} positions, "
        f"trading {'ON' if load_control()['trading'] else 'off (watch mode)'}, lots {ENGINE.get('lot_mode', 'risk')}, "
        f"structure filters {'ON (' + FL.profile() + ')' if FL.enabled() else 'off'}")
    journal("engine_start", symbols=len(feed.symbols))
    kronos = KronosBook(feed)
    log(f"kronos: {', '.join(KB.K['SYMBOLS'])} on {KB.K['TF']}, magic {kronos.magic}, "
        f"{'ON' if KB.enabled() else 'off'} (forecasts from the kronos-signals service)")
    sdd = SddBook(feed)
    log(f"S&D David: {len(sdd.symbols())} symbols on {SB.S['TF']}, limit orders at the zone, target T{SB.S['TARGET']}, "
        f"magic {sdd.magic}, {'ON' if SB.enabled() else 'off'}")
    s_err = ""
    k_err = l_err = ""
    errors = 0
    first = True
    while True:
        t0 = time.time()
        try:
            book.commands()
            while book.mt5_ops:
                term.command(book.mt5_ops.pop(0))
            if not term.ensure_running():
                book.overview(False, term.status)
                time.sleep(float(ENGINE["loop_sec"]))
                continue
            book.read_broker()
            term.check_account(book.account)
            ctl = load_control()
            why = _ready(book)
            trading = ctl["trading"] and not why
            if ctl["trading"] and why and first:
                log(f"trading is on but: {why}")
            tfs = feed.refresh()
            if feed.check_clock():
                log(f"server clock is now {_utc(feed.offset)} (DST): re-reading every timeframe")
                journal("clock", offset_h=feed.offset.total_seconds() / 3600 if feed.offset is not None else None)
                tfs = feed.refresh(force=True)
            if first or "M5" in tfs:
                for s in feed.symbols:
                    try:
                        book.analyse(s, trading)
                    except Exception as e:
                        log(f"{s}: analysis error {type(e).__name__}: {e}")
                        traceback.print_exc()
                first = False
            book.manage()
            try:                                  # Kronos never stops V5: its errors are logged (once each) and skipped
                kronos.step(trading, book.account)
                k_err = ""
            except Exception as e:
                if str(e) != k_err:
                    log(f"kronos: {type(e).__name__}: {e}")
                k_err = str(e)
            try:                                  # DAVID's S&D trades: never stop V5 either
                sdd.step(trading, book.account)
                s_err = ""
            except Exception as e:
                if str(e) != s_err:
                    log(f"sdd: {type(e).__name__}: {e}")
                    traceback.print_exc()
                s_err = str(e)
            try:                                  # the /smc page's live quotes: the same, never stops V5
                LV.step(feed)
                l_err = ""
            except Exception as e:
                if str(e) != l_err:
                    log(f"live: {type(e).__name__}: {e}")
                l_err = str(e)
            book.overview(trading, term.status)
            book.save()
            errors = 0
        except KeyboardInterrupt:
            raise
        except Exception as e:
            errors += 1
            log(f"loop error ({errors}): {type(e).__name__}: {e}")
            if _mt5_error(e):
                term.on_error(e)
            else:
                traceback.print_exc()
            time.sleep(min(60, 5 * errors))
        time.sleep(max(1.0, float(ENGINE["loop_sec"]) - (time.time() - t0)))


def cmd_filters(a) -> int:
    if a.state in ("on", "off"):
        save_control(structure_filters=a.state == "on")
        journal("structure_filters", on=a.state == "on", by="cli")
    elif a.state != "status":
        save_control(filter_profile=a.state)
        journal("filter_profile", profile=a.state, by="cli")
    c = load_control()
    from .config import FILTER_PROFILE, STRUCTURE_FILTERS_ENABLED
    print(f"structure filters {'ON' if FL.enabled() else 'off'} (control.json: {c.get('structure_filters')}, config default: "
          f"{STRUCTURE_FILTERS_ENABLED}); profile {FL.profile()} (control.json: {c.get('filter_profile')}, config default: "
          f"{FILTER_PROFILE}); the running engine picks it up at its next entry attempt")
    return 0


def cmd_kronos(a) -> int:
    if a.state != "status":
        save_control(kronos=a.state == "on")
        journal("kronos", on=a.state == "on", by="cli")
    c = load_control()
    print(f"kronos trading {'ON' if KB.enabled() else 'off'} (control.json: {c.get('kronos')}, config default: {KB.K['ENABLED']}); "
          f"orders also need engine trading {'ON' if c['trading'] else 'off'}; symbols {', '.join(KB.K['SYMBOLS'])}")
    return 0


def cmd_sdd(a) -> int:
    if a.state != "status":
        save_control(sdd=a.state == "on")
        journal("sdd", on=a.state == "on", by="cli")
    c = load_control()
    print(f"S&D David trading {'ON' if SB.enabled() else 'off'} (control.json: {c.get('sdd')}, config default: {SB.S['ENABLED']}); "
          f"orders also need engine trading {'ON' if c['trading'] else 'off'}; {SB.S['TF']}, target T{SB.S['TARGET']}, "
          f"symbols {SB.S['SYMBOLS'] if isinstance(SB.S['SYMBOLS'], str) else ', '.join(SB.S['SYMBOLS'])} (+ {', '.join(SB.S.get('SYMBOLS_EXTRA') or [])})")
    return 0


def cmd_mt5(a) -> int:
    term = Terminal(lambda m: print(m, flush=True), journal)
    if a.op != "status":
        term.command(a.op)
    st = term.status
    unit = __import__("subprocess").run(["systemctl", "--user", "is-active", "mt5-terminal"], capture_output=True, text=True).stdout.strip()
    print(f"mode {term.mode()}  running {term.running()}  unit mt5-terminal {unit}")
    if term.running():
        try:
            acct = mt5c.account()
            print(f"account {acct.get('server')} {acct.get('login')}  connected {acct.get('connected')}  Algo Trading {acct.get('algo_trading')}  "
                  f"equity {acct.get('equity')}")
        except Exception as e:
            print(f"account: {e}")
    if st.get("last_error"):
        print(f"last error: {st['last_error']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="David's V5 engine on MT5 (code only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("once")
    sub.add_parser("run")
    t = sub.add_parser("trading")
    t.add_argument("state", choices=["on", "off"])
    m = sub.add_parser("mt5", help="the MT5 terminal: status, start, stop (stays off), restart, login")
    m.add_argument("op", choices=["status", "start", "stop", "restart", "login"])
    fl = sub.add_parser("filters", help="the structure filter layer: on, off, status, or its profile strict | test | profit (control.json overrides config)")
    fl.add_argument("state", choices=["on", "off", "status", "strict", "test", "profit"])
    kr = sub.add_parser("kronos", help="Kronos' trades (engine/kronos_book.py): on, off, status (control.json overrides config)")
    kr.add_argument("state", choices=["on", "off", "status"])
    sd = sub.add_parser("sdd", help="DAVID's S&D trades (engine/sdd_book.py): on, off, status (control.json overrides config)")
    sd.add_argument("state", choices=["on", "off", "status"])
    a = ap.parse_args()
    return {"check": cmd_check, "once": cmd_once, "run": cmd_run, "trading": cmd_trading, "mt5": cmd_mt5, "filters": cmd_filters,
            "kronos": cmd_kronos, "sdd": cmd_sdd}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
