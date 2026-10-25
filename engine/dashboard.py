"""
engine/dashboard.py — the V5 chart dashboard: every symbol × H4 / H1 / M30 / M15 / M5 with the strategy's
marks (H1 bias swings, M15 supply/demand, displacement, FVG, mitigation block, M5 retracement and BOS,
entry / SL / TP / Target 1 / layer), the live book, and the controls: trading on/off, cancel a setup,
close a setup or a position.

    python3 -m engine.dashboard [--port 8770]          http://127.0.0.1:8770 (loopback only), /backtest = the backtest

It reads only the files the engine writes (engine_data/overview.json, view/<SYMBOL>.json) and never talks
to MT5. Controls are appended to engine_data/commands.jsonl; the running engine applies them within one
loop (15 s). POSTs need the X-V5 header, which a page from another site cannot send without a CORS
preflight this server never answers, so only this page can press the buttons.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .config import COMMANDS_FILE, DATA_DIR, HERE, OVERVIEW_FILE, VIEW_DIR

BT_DIR = os.path.join(DATA_DIR, "backtest")          # written by engine.backtest / bt_report / bt_charts

ACTIONS = {"trading", "cancel_setup", "close_setup", "close_ticket", "mt5"}
MT5_OPS = {"start", "stop", "restart", "login"}
SYM = re.compile(r"^[A-Za-z0-9._#-]{1,24}$")
SETUP_ID = re.compile(r"^[A-Za-z0-9._#-]{1,24}-(M5|M15|M30|H1|H4)-[DS]-\d{6,12}$")


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
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/overview":
            return self._file(OVERVIEW_FILE)
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
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if urlparse(self.path).path != "/api/cmd" or self.headers.get("X-V5") != "1":
            return self._send(403, b'{"error":"forbidden"}')
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            c = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, b'{"error":"bad json"}')
        if c.get("action") not in ACTIONS:
            return self._send(400, b'{"error":"unknown action"}')
        clean = {"action": c["action"]}
        if c["action"] == "trading":
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
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"V5 dashboard on http://127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
