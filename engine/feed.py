"""
engine/feed.py — what the engine trades and the bars it reads, from the MT5 terminal through
~/forex/mt5_client.py (one Wine call per batch).

  symbols   the broker's crypto CFDs that can be opened (full trading, USD profit, a price; no basket
            indexes) and the forex majors (FxPro's "Forex\\Major" folder + AUDUSD / NZDUSD)
  bars      per symbol and timeframe, oldest first, {"t": epoch ms UTC of the bar's start, o h l c v};
            each timeframe is re-read when due (ENGINE["refresh_sec"]); completed() drops the bar still forming
  clock     broker server time minus UTC, measured once from a 24/7 coin's live tick (FxPro: UTC+3)
"""
from __future__ import annotations

import datetime as _dt
import sys
import time
from typing import Dict, List, Optional

from .config import ENGINE, FOREX_DIR

if FOREX_DIR not in sys.path:
    sys.path.insert(0, FOREX_DIR)
import mt5_client as mt5c  # noqa: E402

TF_MIN = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
NOT_CRYPTO = ("ETF", "STOCK", "NASDAQ", "NYSE", "SHARE", "EQUIT", "SYNTH")


def now_ms() -> int:
    return int(time.time() * 1000)


class Feed:
    def __init__(self, cfg: Dict = ENGINE):
        self.cfg = cfg
        self.offset: Optional[_dt.timedelta] = None
        self.symbols: List[str] = []
        self.market: Dict[str, str] = {}          # symbol → "crypto" | "forex"
        self.info: Dict[str, Dict] = {}           # symbol → digits, point, contract, tick value/size, lots, stops level
        self.bars: Dict[tuple, List[Dict]] = {}   # (symbol, tf) → bars
        self.read_at: Dict[str, float] = {}       # tf → time.time() of the last read
        self.clock_at = 0.0                       # time.time() of the last clock re-check (check_clock)

    # ── what to trade ──
    def discover(self) -> List[str]:
        rows: Dict[str, Dict] = {}
        if "crypto" in self.cfg["markets"]:
            for r in mt5c.find("CRYPTO", 300):
                path, desc = str(r.get("path", "")).upper(), str(r.get("description", "")).upper()
                if (any(k in path for k in NOT_CRYPTO) or "INDEX" in desc or r.get("trade_mode") != 4
                        or str(r.get("currency_profit") or "USD").upper() != "USD" or not (r.get("bid") and r.get("ask"))):
                    continue
                rows[r["name"]] = r
                self.market[r["name"]] = "crypto"
        if "forex" in self.cfg["markets"]:
            fx = mt5c.find("FOREX\\MAJOR", 60)
            for name in self.cfg.get("forex_extra") or []:
                fx += [r for r in mt5c.find(name, 5) if r["name"] == name]
            for r in fx:
                if r.get("trade_mode") == 4 and str(r.get("path", "")).upper().startswith("FOREX"):
                    rows[r["name"]] = r
                    self.market[r["name"]] = "forex"
        names = sorted(rows, key=lambda s: (self.market[s] != "crypto", s not in ("BITCOIN", "ETHEREUM"), s))
        res = mt5c.call([{"op": "info", "symbol": s} for s in names], timeout=180)
        for s, r in zip(names, res):
            if "result" in r:
                self.info[s] = r["result"]
        self.symbols = [s for s in names if s in self.info]
        return self.symbols

    def detect_clock(self) -> Optional[_dt.timedelta]:
        """Server minus UTC from a coin that is ticking now; None = MetaQuotes' New York + 7 h rule."""
        for s in [x for x in self.symbols if self.market.get(x) == "crypto"][:3]:
            try:
                self.offset = mt5c.detect_offset(s)
                return self.offset
            except Exception:
                continue
        return self.offset

    def check_clock(self) -> bool:
        """The server clock moves with DST (FxPro UTC+3 → UTC+2 on 2026-10-25): bars stamped with the old offset
        look an hour old (the forming bar would pass as completed) or an hour ahead (the last hour unseen). A 24/7
        coin's newest M5 bar must have started within the last few minutes; when it hasn't, measure the offset
        again (at most every 10 min). → True when it changed: the caller re-reads every timeframe."""
        coins = [s for s in self.symbols if self.market.get(s) == "crypto"]
        m5 = self.get(coins[0], "M5") if coins else []
        if not m5 or -120_000 <= now_ms() - m5[-1]["t"] <= 600_000 or time.time() - self.clock_at < 600:
            return False
        self.clock_at = time.time()
        old = self.offset
        self.detect_clock()
        return self.offset != old

    # ── bars ──
    def due(self, force: bool = False) -> List[str]:
        now = time.time()
        return [tf for tf in self.cfg["bars"] if force or now - self.read_at.get(tf, 0) >= self.cfg["refresh_sec"].get(tf, 60)]

    def refresh(self, force: bool = False) -> List[str]:
        """Re-read the timeframes that are due, for every symbol, in one bridge call. → the timeframes read."""
        tfs = self.due(force)
        if not tfs:
            return []
        wants = [(s, tf, self.cfg["bars"][tf]) for tf in tfs for s in self.symbols]
        got = mt5c.bars_many(wants, timeout=300, offset=self.offset)
        for k, v in got.items():
            self.bars[k] = v
        for tf in tfs:
            self.read_at[tf] = time.time()
        return tfs

    def get(self, sym: str, tf: str) -> List[Dict]:
        return self.bars.get((sym, tf), [])

    def completed(self, sym: str, tf: str, at_ms: Optional[int] = None) -> List[Dict]:
        """Bars that had closed by `at_ms` (default now): the analysis never looks at the forming bar."""
        cut = (at_ms or now_ms()) - TF_MIN[tf] * 60_000
        return [b for b in self.get(sym, tf) if b["t"] <= cut]

    def last_price(self, sym: str) -> Optional[float]:
        b = self.get(sym, "M5")
        return b[-1]["c"] if b else None
