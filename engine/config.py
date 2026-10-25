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
    "bias_exempt_tfs": ["M15", "M30"],   # David 2026-10-25 evening: M15 / M30 entries trade on their own structure,
                                         # no higher-TF bias needed (bias still computed and shown on the cards)
    "normal_entry": True, "layer_entry": True, "dynamic_layer": True,
    "max_normal_entries": 1, "max_layer_entries": 1, "max_entries_per_setup": 2,
    "layer_target_1": True, "normal_target_near_protection": True, "layer_profit_protection": True,
    "structure_trailing": True, "trailing_tf": "M5",
    "never_widen_sl": True,
    "max_running_trades": 20,            # simultaneously open positions (normal + layer), not per day
    # David 2026-10-24: BOS first → supply (downtrend) / demand (uptrend) in the BOS move, or the mitigation
    # block when there is no supply / demand → the FVG inside the BOS move → entry when price comes back to it
    "bos": "required", "supply_demand": "or mitigation block", "mitigation_block": "when no supply/demand", "fvg": "required",
    "fvg_pick": "nearest",               # new rules §15 (David 2026-10-25): one displacement's FVGs are ONE cluster,
                                         # the retrace trigger is its nearest FVG ("nearest"); an int = that one, left to right (old: 2)
    "fvg_entry_depth": 0.10,             # entry 10 % inside that FVG, from the side price comes back from
    # David 2026-10-25 (COSMOS M30): the entry FVG must stay untouched for the next candles after it completes,
    # then price must run on before the retrace — a pullback earlier than both is an invalid structure
    "fvg_protect_candles": 2,            # candles after the FVG that must not trade back into it
    "fvg_min_runoff_atr": 0.5,           # × ATR(14, own TF) price must run beyond the FVG before the retrace
    # new rules §18 (David 2026-10-25): the M15/M30 BOS only VALIDATES the zone; the entry needs its own proof —
    # after the retrace into the zone + FVG area, an M5 candle must CLOSE beyond the latest confirmed M5 swing
    "entry_confirm": "M5",               # None / "" = enter at the touch (the engine before 2026-10-25 16:30)
    "m5_confirm_max_bars": 36,           # give up when no M5 entry BOS this many M5 candles after the retrace (3 h)

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
    "server_tz": "Asia/Nicosia",         # FxPro's server clock: UTC+2, UTC+3 in EU summer time (switched 2026-10-25)
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

# ── structure-quality filter layer (David 2026-10-25, branch feature/structure-filters; engine/filters.py) ──
# Eight hard gates checked right before any order. False = the engine behaves exactly as before the layer.
# control.json "structure_filters" (python3 -m engine.run filters on|off) overrides this while the engine runs.
STRUCTURE_FILTERS_ENABLED = True
FILTERS = {
    "ATR_PERIOD": 14,                    # every ATR(14) below, on the timeframe each gate names
    # Gate 1 swing significance: a fractal with SWING_LEFT / SWING_RIGHT candles each side whose leg from the
    # previous significant swing is ≥ SWING_MIN_LEG_ATR × ATR; smaller pivots are not structure
    "SWING_LEFT": 3, "SWING_RIGHT": 3, "SWING_MIN_LEG_ATR": 1.0,
    # Gate 2 break quality: body close beyond the swing; the breaking move (1-3 candles) ranges ≥ 1.5 ATR and
    # leaves an FVG ≥ 0.3 ATR; the entry FVG untraded until the entry attempt. Else the break is "drift"
    "DISPLACEMENT_MAX_CANDLES": 3, "DISPLACEMENT_MIN_ATR": 1.5, "FVG_MIN_ATR": 0.3,
    # Gate 3 regime on the setup's timeframe: trend = last two structural points agree with the side;
    # the last 4 significant swings inside a band < 3 ATR = RANGE → no trade
    "RANGE_SWINGS": 4, "RANGE_BAND_ATR": 3.0,
    # Gate 4 bias: H4 and H1 bias = the BOS side, M30 trend not against the H4 bias
    "BIAS_TFS": ["H4", "H1"], "NOT_AGAINST_TF": "M30",
    # Gate 5 location: the BOS impulse starts in the discount (longs) / premium (shorts) part of the current
    # H4 leg, from a fresh zone; the nearest opposing structure ≥ MIN_ROOM_R × the stop distance away
    "LOCATION_TF": "H4", "PD_SPLIT": 0.5, "MIN_ROOM_R": 3.0,
    "PD_REQUIRED": True, "ZONE_FRESH_REQUIRED": True,     # False: measured and logged, not required
    # Gate 6 stop and RR: S&D H4 entered on M15 → SL beyond the M15 swing that started the M15 break +
    # spread + 0.25 × ATR(M15); stop distance ≥ stops level, ≥ 3 × spread, ≤ 3 × ATR(M15);
    # TP = nearest opposing structure, RR ≥ 3 after the SL is final (never stretched); SL / TP on the tick size
    "SL_ATR_BUFFER": 0.25, "SL_MIN_SPREAD_X": 3.0, "SL_MAX_ATR": 3.0, "MIN_RR": 3.0,
    "SL_WIDEN_TO_STOPS_LEVEL": False,    # True: a stop inside the broker's stops level moves out to it instead of refusing
    "TARGET_TFS": ["H1", "H4"],          # + the setup's own timeframe
    # Gate 7 expiry: price back in the FVG within 12 M15 candles of the setup forming; a CHoCH against it
    # before the fill cancels it; one trade per H4 zone; no new trade on a zone that already lost
    "SETUP_EXPIRY_M15_BARS": 12, "ONE_TRADE_PER_H4_ZONE": True, "NO_REENTRY_AFTER_LOSS": True,
    # Gate 8 volatility / spread / session
    "ATR_MIN_PCTL": 30, "ATR_PCTL_BARS": 200,             # ATR(14, M15) ≥ its 30th percentile of 200 bars
    "SPREAD_MAX_X_AVG": 1.5, "SPREAD_AVG_BARS": 20,       # spread ≤ 1.5 × the 20 M15 bars' average
    # sessions in their own local time (summer time follows); a symbol trades only inside its sessions
    "SESSIONS": {"Sydney": ["Australia/Sydney", "08:00", "17:00"], "Tokyo": ["Asia/Tokyo", "09:00", "18:00"],
                 "London": ["Europe/London", "08:00", "17:00"], "NewYork": ["America/New_York", "08:00", "17:00"]},
    "SYMBOL_SESSIONS": {"crypto": "24/7", "forex": ["London", "NewYork"],
                        "AUDUSD": ["Sydney", "Tokyo", "London", "NewYork"], "NZDUSD": ["Sydney", "Tokyo", "London", "NewYork"],
                        "USDJPY": ["Tokyo", "London", "NewYork"], "EURJPY": ["Tokyo", "London", "NewYork"],
                        "GBPJPY": ["Tokyo", "London", "NewYork"], "CADJPY": ["Tokyo", "London", "NewYork"],
                        "CHFJPY": ["Tokyo", "London", "NewYork"]},
    # logging and limits
    "MAX_POSITIONS": 5,                  # open positions + pending layers (replaces max_running_trades while on)
    "TEST_LOT": 0.01,                    # lot_mode "min": max(0.01, the symbol's volume_min)
    "LOG_DIR": os.path.join(DATA_DIR, "filters"),        # candidates-YYYY-MM-DD.jsonl (IST date), one record per decision
}
# Profiles: overrides on top of FILTERS. "strict" = the spec as written (0 of 1,482 attempts passed in the 7-day
# replay); "test" = what the engine trades in the 0.01-lot test (David 2026-10-25: "consider the new logic and take
# the entry"). control.json "filter_profile" (python3 -m engine.run filters strict|test) overrides FILTER_PROFILE.
FILTER_PROFILE = "test"
FILTER_PROFILES = {
    "strict": {},
    # 120-day replay (strict took 2, both lost; V5 alone took 352, -33 R): 19 trades, 6 won, +16.1 R
    "test": {"MIN_RR": 2.0, "MIN_ROOM_R": 2.0, "PD_REQUIRED": False, "ZONE_FRESH_REQUIRED": False,
             "SL_WIDEN_TO_STOPS_LEVEL": True},
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
