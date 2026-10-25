"""
engine/config.py — the V5 strategy inputs (as David wrote them, 2026-10-24) and the engine's own settings.

The strategy inputs are section 41 of "MT5 EA — COMPLETE FINAL STRATEGY LOGIC V5". Where the strategy
text describes judgement in words (layer depth by movement strength, "very close to the final target and
reversal begins", Target 1 "at a centre level", progressive protection at 3R/4R/5R+), the measurable
choices are here too, named and commented, so they can be tuned without touching the logic.

control.json (written by the dashboard) holds what can change while the engine runs: trading on/off.
"""
from __future__ import annotations

import json
import os
from typing import Dict

HERE = os.path.dirname(os.path.abspath(__file__))
FOREX_DIR = os.path.dirname(HERE)
DATA_DIR = os.path.join(FOREX_DIR, "engine_data")
VIEW_DIR = os.path.join(DATA_DIR, "view")            # one JSON per symbol: bars + markings for the dashboard
STATE_FILE = os.path.join(DATA_DIR, "state.json")    # setups and the positions that belong to them
JOURNAL_FILE = os.path.join(DATA_DIR, "journal.jsonl")
OVERVIEW_FILE = os.path.join(DATA_DIR, "overview.json")
CONTROL_FILE = os.path.join(DATA_DIR, "control.json")
COMMANDS_FILE = os.path.join(DATA_DIR, "commands.jsonl")  # dashboard → engine: cancel / close / trading on-off
for _d in (DATA_DIR, VIEW_DIR):
    os.makedirs(_d, exist_ok=True)

STRATEGY = {
    # ── section 41: default EA inputs ──
    "normal_risk_pct": 2.5,
    "layer_risk_pct": 1.5,
    "max_combined_risk_pct": 4.0,
    "min_rr": 3.0,                       # no maximum RR
    "swing_length": 2,
    "displacement_mult": 1.5,
    "body_average_bars": 10,
    "sl_buffer_points": 20,
    # David 2026-10-24 SL/TP bug fix: the SL comes only from the setup's own zone + buffer; a stop farther than
    # sl_max_atr_mult × the ATR (sl_atr_tf, sl_atr_period) is abnormal → no trade (never moved closer to pass)
    "sl_max_atr_mult": 3.0, "sl_atr_tf": "M15", "sl_atr_period": 14,
    "bias_tfs": ["H4", "H1"],            # David 2026-10-25: the H4 and the H1 bias must agree (was H1 only)
    "normal_entry": True, "layer_entry": True, "dynamic_layer": True,
    "max_normal_entries": 1, "max_layer_entries": 1, "max_entries_per_setup": 2,
    "layer_target_1": True, "normal_target_near_protection": True, "layer_profit_protection": True,
    "structure_trailing": True, "trailing_tf": "M5",
    "never_widen_sl": True,
    "max_running_trades": 20,            # simultaneously open positions (normal + layer), not per day
    # David 2026-10-24: BOS first → supply (downtrend) / demand (uptrend) in the BOS move, or the mitigation
    # block when there is no supply / demand → the FVG inside the BOS move → entry when price comes back to it
    "bos": "required", "supply_demand": "or mitigation block", "mitigation_block": "when no supply/demand", "fvg": "required",
    "fvg_pick": 2,                       # with two or more FVGs in the BOS move: the 2nd, counted left to right
    "fvg_entry_depth": 0.10,             # entry 10 % inside that FVG, from the side price comes back from

    # ── measurable choices for the parts described in words ──
    # 3/4: the zone = the final opposite candle within this many bars before the move's first displacement
    "zone_lookback_bars": 5,
    # BOS setups older than this (bars of their own timeframe) and never reached are dropped
    "setup_max_age_bars": 192,
    # the entry counts only when the engine sees price reach it live (latest or forming M5 bar), never late
    # 13/14: dynamic layer depth as a share of entry→SL by movement strength (weak / moderate / strong)
    "layer_depth": {"weak": 0.25, "moderate": 0.40, "strong": 0.55},
    "strength_body_ratio": 1.3,          # retracement candles' average body vs the 20 before: "big"
    "strength_consecutive": 4,           # candles in a row in the retracement direction: "persistent"
    "strength_travel_atr": 1.5,          # distance travelled in the retracement, in M5 ATRs: "far"
    # 22: "very close to the final target and reversal begins"
    "near_target_progress": 0.80,        # best price reached ≥ 80 % of the way from entry to the final target
    "reversal_giveback": 0.10,           # ...then gave back ≥ 10 % of the way, or an M5 candle closed against
    # 26: Layer Target 1 between the normal entry and the final target (0.5 = centre)
    "tp1_fraction": 0.5,
    # 27/28: after TP1 the stop goes past the first normal entry by this share of its risk (min sl_buffer_points)
    "tp1_lock_r": 0.1,
    # 31: protection steps once the trade is ≥ 3R: at nR the stop locks at least (n − 2)R
    "lock_start_r": 3.0, "lock_gap_r": 2.0,
    # 18/19: the final target is the first opposite structure level (setup-timeframe / H1 / H4 swing that price
    # has not traded through) at ≥ min_rr; with none in reach → no trade (David 2026-10-24: never a made-up 3R)
}

ENGINE = {
    "magic": 5050505,                    # tags this engine's orders and positions
    "markets": ["crypto", "forex"],      # David 2026-10-24: the FxPro coins + the forex majors
    "forex_extra": ["AUDUSD", "NZDUSD"], # standard majors FxPro files outside its "Major" folder
    "chart_tfs": ["H4", "H1", "M30", "M15", "M5"],   # dashboard: David's four + M5
    "setup_tfs": ["H4", "H1", "M30", "M15", "M5"],   # BOS → zone → FVG found and drawn on every chart timeframe
    "trade_tfs": ["M15", "M30"],         # ...but only these may enter (David 2026-10-24: they finish fast → more trades to study)
    # David 2026-10-25, the third entry "S&D H4": price back at an H4 setup's entry → an M15 BOS / CHoCH the same way
    # from inside the H4 zone → that M15 move's own zone + FVG → entry 10 % inside it (an M15 trade, SL = M15 zone)
    "sdh4": {"zone_tf": "H4", "confirm_tf": "M15"},
    "bars": {"H4": 150, "H1": 300, "M30": 200, "M15": 400, "M5": 400},
    "view_bars": {"H4": 90, "H1": 120, "M30": 120, "M15": 140, "M5": 160},
    "refresh_sec": {"M5": 60, "M15": 60, "M30": 300, "H1": 300, "H4": 900},
    "loop_sec": 15,                      # positions are managed this often; analysis runs on each new M5 bar
    "stops_level_margin": 1.1,           # a stop / target must clear the broker's stops level by 10 % (from the closing price)
    "max_spread_frac": 0.35,             # NOT in V5: refuse an entry whose spread is over 35 % of its stop distance
    "demo_only": True,
    # David 2026-10-25: "make the qty minimum like 1 micro lot, we have to test our engine": every normal and layer
    # order at the symbol's minimum lot (volume_min, 0.01) instead of 2.5 % / 1.5 % risk; "risk" = V5 sizing
    "lot_mode": "min",
    # the account the engine keeps the terminal logged in to (engine/terminal.py)
    "mt5_login": 592224888, "mt5_server": "FxPro-MT5 Demo",
}


def load_control() -> Dict:
    try:
        with open(CONTROL_FILE) as f:
            c = json.load(f)
    except Exception:
        c = {}
    return {"trading": bool(c.get("trading", False)), **{k: v for k, v in c.items() if k != "trading"}}


def save_control(**kw) -> Dict:
    c = {**load_control(), **kw}
    tmp = CONTROL_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f, indent=1)
    os.replace(tmp, CONTROL_FILE)
    return c
