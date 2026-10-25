"""
engine/terminal.py — the engine runs the MT5 terminal itself (David 2026-10-25: "give the control to the engine:
open, close, restart, login, all things").

The terminal is the systemd user unit mt5-terminal (Wine, ~/.mt5), so it lives apart from the engine: an engine
restart does not close it, and stopping the unit closes the terminal together with its wineserver. Every loop:

  not running              → start it (unless control.json "mt5" is "off": stopped from the dashboard / CLI)
  MT5 calls fail           → twice in a row, or once with a broken Wine ("wineserver ... not upgraded": Wine updated
                             under a running terminal, 2026-10-25) → restart: the unit, any stray terminal / wineserver
                             of this prefix, start again
  not connected            → 2 min to reconnect by itself, then restart
  logged out / other login → log in to ENGINE["mt5_login"] on ENGINE["mt5_server"] (the terminal's saved password,
                             or MT5_PASSWORD from engine_data/mt5.env)
  Algo Trading off         → common.ini [Experts] Enabled=1 (the button's saved state) and restart, at most hourly

Restarts back off: never two within 3 min; after 5 in an hour only every 15 min, and the dashboard says so.

    python3 -m engine.run mt5 status|start|stop|restart|login        (the dashboard has the same buttons)
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Callable, Dict, List, Optional

from .config import DATA_DIR, ENGINE, load_control, save_control
from .feed import mt5c

UNIT = "mt5-terminal"
PREFIX = mt5c.WINEPREFIX
COMMON_INI = os.path.join(PREFIX, "drive_c", "Program Files", "MetaTrader 5", "Config", "common.ini")
ENV_FILE = os.path.join(DATA_DIR, "mt5.env")        # optional, chmod 600: MT5_PASSWORD=...
RESTART_GAP = 180                                   # s between restarts
BURST, BURST_WINDOW, SLOW_GAP = 5, 3600, 900        # after 5 restarts in an hour: one per 15 min
DISCONNECT_GRACE = 120
READY_WAIT = 150


def _sh(*cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)


def _pids(pattern: str) -> List[int]:
    r = _sh("pgrep", "-f", pattern)
    return [int(x) for x in r.stdout.split()] if r.returncode == 0 else []


def _prefix_wineservers() -> List[int]:
    """wineserver processes of THIS prefix only (LTspice and others run their own): a wineserver's working
    directory is /tmp/.wine-<uid>/server-<dev>-<inode of the prefix>."""
    st = os.stat(PREFIX)
    tag = f"server-{st.st_dev:x}-{st.st_ino:x}"
    out = []
    for pid in _pids(r"[w]ineserver"):
        try:
            if os.readlink(f"/proc/{pid}/cwd").endswith(tag):
                out.append(pid)
        except OSError:
            pass
    return out


def _password() -> Optional[str]:
    try:
        with open(ENV_FILE) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                if k == "MT5_PASSWORD" and v:
                    return v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return None


def set_algo_enabled(path: str = COMMON_INI) -> bool:
    """[Experts] Enabled=1 in common.ini (UTF-16), read by the terminal when it starts. → True if it changed."""
    with open(path, "rb") as f:
        text = f.read().decode("utf-16")
    out, section, changed = [], "", False
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("["):
            section = s
        elif section == "[Experts]" and s.replace(" ", "") == "Enabled=0":
            line, changed = line.replace("0", "1", 1), True
        out.append(line)
    if changed:
        with open(path, "wb") as f:
            f.write("".join(out).encode("utf-16"))
    return changed


class Terminal:
    """State of the supervisor; `log` / `journal` are the engine's (book.log / book.journal)."""

    def __init__(self, log: Callable[[str], None], journal: Callable[..., None]):
        self.log, self.journal = log, journal
        self.restarts: List[float] = []
        self.errors = 0
        self.disconnected_since: Optional[float] = None
        self.algo_fix_at = 0.0
        self.login_tried_at = 0.0
        self.status: Dict = {"mode": self.mode(), "running": None, "connected": None, "login": None, "algo": None,
                             "last_action": None, "last_error": None, "waiting": None}

    # ── control.json "mt5": auto (the engine keeps it running) | off (stopped on purpose) ──
    @staticmethod
    def mode() -> str:
        return "off" if load_control().get("mt5") == "off" else "auto"

    def running(self) -> bool:
        return mt5c.terminal_running()

    def _act(self, what: str, **kw) -> None:
        self.status["last_action"] = f"{time.strftime('%a %H:%M')} {what}"
        self.log(f"MT5: {what}")
        self.journal("mt5", action=what, **kw)

    # ── start / stop / restart ──
    def start(self, wait: bool = True) -> bool:
        if not self.running():
            r = _sh("systemctl", "--user", "start", UNIT)
            self._act("start", ok=r.returncode == 0, out=r.stdout.strip()[-200:])
            # no MT5 call until the terminal has started its own wineserver: a call that comes first starts it in
            # the caller's cgroup (the engine's), and an engine restart would then take MT5 down with it
            t0 = time.time()
            while time.time() - t0 < 60 and not (self.running() and _prefix_wineservers()):
                time.sleep(1)
            time.sleep(5)
        return self.wait_ready() if wait else True

    def wait_ready(self, limit: float = READY_WAIT) -> bool:
        """Until a call answers and the terminal is connected to the server."""
        t0 = time.time()
        while time.time() - t0 < limit:
            try:
                a = mt5c.account()
                if a.get("connected"):
                    self.errors = 0
                    self.status.update(running=True, connected=True, login=a.get("login"), algo=a.get("algo_trading"), last_error=None)
                    return True
            except Exception as e:
                self.status["last_error"] = str(e)[-200:]
            time.sleep(5)
        self.status["last_error"] = f"not ready after {limit:.0f} s: {self.status.get('last_error')}"
        return False

    def stop(self) -> None:
        """The unit (terminal + its wineserver), then anything of this prefix left over (a terminal started by hand,
        or the old wineserver after a Wine update, which the new wineserver binary can no longer talk to)."""
        _sh("systemctl", "--user", "stop", UNIT, timeout=60)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            left = _pids(r"[t]erminal64\.exe")
            for pid in left:
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass
            for _ in range(15):
                if not _pids(r"[t]erminal64\.exe"):
                    break
                time.sleep(1)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for pid in _prefix_wineservers():
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass
            time.sleep(2)
        self.status.update(running=False, connected=False)

    def may_restart(self, now: Optional[float] = None) -> Optional[str]:
        """None = a restart may go now, else why not yet."""
        now = time.time() if now is None else now
        recent = [t for t in self.restarts if now - t < BURST_WINDOW]
        gap = SLOW_GAP if len(recent) >= BURST else RESTART_GAP
        if self.restarts and now - self.restarts[-1] < gap:
            return f"last restart {now - self.restarts[-1]:.0f} s ago (next after {gap} s" + \
                   (f"; {len(recent)} restarts this hour)" if len(recent) >= BURST else ")")
        return None

    def restart(self, why: str, fix_algo: bool = False, force: bool = False) -> bool:
        wait = None if force else self.may_restart()
        if wait:
            self.status["waiting"] = f"restart wanted ({why}) — {wait}"
            return False
        self.restarts.append(time.time())
        self.status["waiting"] = None
        self._act(f"restart ({why})")
        self.stop()
        if fix_algo:
            try:
                if set_algo_enabled():
                    self._act("Algo Trading switched on in common.ini")
            except Exception as e:
                self.log(f"MT5: could not edit common.ini: {e}")
        ok = self.start()
        self._act("ready" if ok else f"NOT ready: {self.status.get('last_error')}")
        return ok

    def login(self) -> bool:
        want, server = ENGINE.get("mt5_login"), ENGINE.get("mt5_server")
        if not want:
            return False
        self.login_tried_at = time.time()
        q = {"op": "login", "login": int(want), "server": server}
        pw = _password()
        if pw:
            q["password"] = pw
        try:
            r = mt5c.one(q, timeout=120)
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        self._act(f"login {want} on {server}: {'OK' if r.get('ok') else 'FAILED ' + str(r.get('error'))}")
        return bool(r.get("ok"))

    # ── called by the engine every loop ──
    def ensure_running(self) -> bool:
        """Before the loop touches MT5: True when the terminal may be used now."""
        self.status["mode"] = self.mode()
        if self.status["mode"] == "off":
            self.status["running"] = self.running()
            return False
        if self.running():
            self.status["running"] = True
            return True
        self.status["running"] = False
        if self.restarts and self.may_restart():
            self.status["waiting"] = f"terminal down — {self.may_restart()}"
            return False
        self.restarts.append(time.time())
        ok = self.start()
        self._act("ready" if ok else f"NOT ready: {self.status.get('last_error')}")
        return ok

    def on_error(self, e: Exception) -> None:
        """An MT5 call failed."""
        msg = str(e)
        self.errors += 1
        self.status["last_error"] = msg[-200:]
        broken_wine = "wineserver" in msg or "not upgraded" in msg
        if broken_wine or self.errors >= 2:
            self.restart("Wine was updated under the running terminal" if broken_wine else f"{self.errors} failed calls: {msg[-120:]}")

    def check_account(self, a: Dict) -> None:
        """After a good read: connection, login, Algo Trading."""
        self.errors = 0
        now = time.time()
        self.status.update(running=True, connected=a.get("connected"), login=a.get("login"), algo=a.get("algo_trading"),
                           server=a.get("server"))
        if not a.get("connected"):
            self.disconnected_since = self.disconnected_since or now
            if now - self.disconnected_since > DISCONNECT_GRACE:
                self.restart(f"not connected to the server for {now - self.disconnected_since:.0f} s")
            return
        self.disconnected_since = None
        want = ENGINE.get("mt5_login")
        if want and a.get("login") != int(want) and now - self.login_tried_at > RESTART_GAP:
            self.login()
            return
        if not a.get("algo_trading") and now - self.algo_fix_at > BURST_WINDOW:
            self.algo_fix_at = now
            self.restart("Algo Trading is off", fix_algo=True)

    def command(self, op: str) -> None:
        """From the dashboard or the CLI: start / stop / restart / login."""
        if op == "stop":
            save_control(mt5="off")
            self._act("stop (by hand: stays off until start)")
            self.stop()
        elif op == "start":
            save_control(mt5="auto")
            self.start()
            self._act("ready" if self.status.get("connected") else f"NOT ready: {self.status.get('last_error')}")
        elif op == "restart":
            save_control(mt5="auto")
            self.restart("by hand", force=True)
        elif op == "login":
            self.login()
