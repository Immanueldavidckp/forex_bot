"""
engine/fib_reject.py — the LIVE versions of the class's Fib rules and their reject checklist (David 2026-11-12: "now
update these strategies to the live"), from the research in engine/research/fib_trend (improve.py, reject.py):

    retrace   FIB RETRACEMENT at every BOS leg: limit at 0.382, stop 0.1 ATR under the swing low (Fib 0), target 2R.
              Rejected on 2 or more warnings. 2023–2026 (never seen when the warnings were chosen): 6,080 trades kept at
              +0.02 R after the spread (t 1.1); the 3,376 rejected made −0.04 R.
    trend     FIB GO WITH TREND, entry as taught (next candle through the 0.618 candle's high), stop 0.1 ATR under the
              swing low, target 2R. Rejected on ANY warning. 2023–2026: 1,446 kept at +0.04 R (t 1.1); 2,776 rejected
              at −0.11 R.
    Small edges, not proven: the live demo run is the test.

The warnings are read when a candle closes, for the order that would work during the next candle (the backtest read
them at the entry candle's open, from the candle before): market, session and weekday of that next candle (UTC), the
spread ÷ the stop distance, where the entry sits in the last 100 candles' range (1 = the expensive end for this trade),
the swing's size in ATR and its number from the CHoCH, and how far price has run from EMA 21 (in ATR, the trade's way).
The numbers are the 2018–2022 fifths' edges.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import fib_trend as F
from .major_structure import atr14

PARAMS = {
    "retrace": {"mode": "every", "entry_fib": 0.382, "stop_fib": 0.0, "stop_buffer_atr": 0.1, "target_r": 2.0},
    "trend": {"stop_fib": 0.0, "target_r": 2.0, "min_rr": 0},
}
REJECT = {
    "retrace": {"need": 2, "sym": {"CADCHF", "EURCAD", "GBPCHF"}, "sess": {"NewYork"}, "dow": set(),
                "cost_gt": 0.156, "rng_gt": 0.83, "swing_atr_le": 2.65, "ext_gt": 1.58, "swing": {4}},
    "trend": {"need": 1, "sym": {"CADCHF", "GBPCAD", "EURCHF", "EURCAD", "USDCAD"}, "sess": {"late", "Asia"}, "dow": {1},
              "cost_gt": 0.108},
}
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def setups(rule: str, bars: List[Dict], m: Optional[Dict] = None) -> List[Dict]:
    """the live version's setups (the same code the /smc layer draws and the book trades)"""
    m = m or F.swing_structure(bars, F.STRUCTURE_N)
    return F.setups(bars, m, **PARAMS["trend"]) if rule == "trend" else F.retrace_setups(bars, m, **PARAMS["retrace"])


def session(t_ms: int) -> str:
    h = (t_ms // 3600_000) % 24
    return "Asia" if h < 7 else "London" if h < 13 else "NewYork" if h < 21 else "late"


def context(bars: List[Dict]) -> Dict:
    """per-candle series the warnings read: Wilder ATR(14) (+ ÷ its 200-candle median), EMA 21, the 100-candle high /
    low, atr14"""
    tr, atr, vol, hi, lo = [], [], [], [], []
    for i, b in enumerate(bars):
        t = b["h"] - b["l"] if i == 0 else max(b["h"] - b["l"], abs(b["h"] - bars[i - 1]["c"]), abs(b["l"] - bars[i - 1]["c"]))
        atr.append(t if i == 0 else atr[-1] + (t - atr[-1]) / 14)
    for i in range(len(bars)):
        w = sorted(atr[max(0, i - 199):i + 1])
        n = len(w)
        med = w[n // 2] if n % 2 else (w[n // 2 - 1] + w[n // 2]) / 2
        vol.append(atr[i] / med if med else 1.0)
        seg = bars[max(0, i - 99):i + 1]
        hi.append(max(x["h"] for x in seg))
        lo.append(min(x["l"] for x in seg))
    return {"vol": vol, "hi": hi, "lo": lo, "atr14": atr14(bars), "atr": atr, "e21": F.ema([b["c"] for b in bars], 21)}


def warnings(rule: str, sym: str, s: Dict, bars: List[Dict], ctx: Dict, j: int, px: float, spread: Optional[float] = None) -> List[str]:
    """the warnings for setup s if its order works during candle j (j = len(bars) for the candle now forming), entry px.
    spread None (the chart's history has none) → the spread warning is not checked."""
    R = REJECT[rule]
    k = min(j - 1, len(bars) - 1)                                    # the last closed candle before j
    step = bars[1]["t"] - bars[0]["t"] if len(bars) > 1 else 0
    t = bars[j]["t"] if j < len(bars) else bars[-1]["t"] + step
    buy = s["side"] == "buy"
    out = []
    if sym in R["sym"]:
        out.append(f"market {sym}")
    if session(t) in R["sess"]:
        out.append(f"session {session(t)}")
    d = int((t // 86400_000 + 3) % 7)
    if d in R["dow"]:
        out.append(DOW[d])
    risk = abs(px - s["sl"]) if s.get("sl") is not None else 0
    if spread is not None and risk and R.get("cost_gt") is not None and spread / risk > R["cost_gt"]:
        out.append(f"spread {spread / risk:.0%} of the stop (over {R['cost_gt']:.0%})")
    if R.get("rng_gt") is not None:
        span = ctx["hi"][k] - ctx["lo"][k]
        rng = (px - ctx["lo"][k]) / span if span else 0.5
        rng = rng if buy else 1 - rng
        if rng > R["rng_gt"]:
            out.append(f"entry at {rng:.0%} of the 100-candle range (expensive end)")
    if R.get("swing_atr_le") is not None and s.get("h_idx") is not None and s.get("L") is not None:
        a = ctx["atr14"][s["h_idx"]]
        if a and abs(s["H"] - s["L"]) / a <= R["swing_atr_le"]:
            out.append(f"small swing ({abs(s['H'] - s['L']) / a:.1f} ATR)")
    if R.get("ext_gt") is not None and ctx["atr"][k]:
        ext = (bars[k]["c"] - ctx["e21"][k]) * (1 if buy else -1) / ctx["atr"][k]
        if ext > R["ext_gt"]:
            out.append(f"price {ext:.1f} ATR past EMA 21 (stretched)")
    if s.get("swing") in R.get("swing", ()):
        out.append(f"swing {s['swing']}")
    if R.get("vol_le") is not None and ctx["vol"][k] <= R["vol_le"]:
        out.append(f"quiet market (ATR {ctx['vol'][k]:.2f} × normal)")
    return out


def judged(rule: str, sym: str, bars: List[Dict], m: Optional[Dict] = None) -> List[Dict]:
    """setups() with each setup's warnings (at its entry candle, or for the next candle while it waits) and
    "rejected": True when the checklist refuses it — for the /smc layer (no spread there) and the live book"""
    ss = setups(rule, bars, m)
    ctx = context(bars)
    for s in ss:
        j = s["entry_idx"] if s.get("entry_idx") is not None else len(bars)
        px = s["entry"] if s.get("entry_idx") is not None else s.get("mark") if rule == "trend" else s.get("entry_level")
        live = s.get("entry_idx") is not None or s["status"] in ("buy stop", "sell stop", "buy limit", "sell limit")
        s["warnings"] = warnings(rule, sym, s, bars, ctx, j, px, None) if live and px is not None and s.get("sl") is not None else []
        s["rejected"] = len(s["warnings"]) >= REJECT[rule]["need"]
    return ss
