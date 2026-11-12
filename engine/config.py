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
CHART_EXTRA = ["GOLD"]   # on the /smc page although the V5 engine does not trade them: always read live (live.py)
LIVE_DIR = os.path.join(DATA_DIR, "live")            # one JSON per symbol a /smc page watches: tick + latest bars (live.py)
STATE_FILE = os.path.join(DATA_DIR, "state.json")    # setups and the positions that belong to them
JOURNAL_FILE = os.path.join(DATA_DIR, "journal.jsonl")
OVERVIEW_FILE = os.path.join(DATA_DIR, "overview.json")
PNL_FILE = os.path.join(DATA_DIR, "pnl.json")       # the 24/7 profit report (engine/pnl.py), written by the engine
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
    # learning chart 2026-10-26 (David's EURUSD M15 labels): the trend only turns at MAJOR structure — a
    # retrace poking over a minor LH / under a minor HL is not a CHoCH (it kept flipping the engine's bias
    # and pruning the real BOS levels). Major swings = fractals this many bars each side.
    "major_swing_length": 4,
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
    # David 2026-10-30: "take all the valid trade, no limit for trade and position, lot 0.01". Same structure
    # gates as "test" (so nothing valid is turned away), every cap lifted, and the cost gate G9 doing the work
    # -- measured: direction is a coin flip (gross -$0.024/trade, t=-1.91), the spread is the entire P&L.
    "profit": {"MIN_RR": 2.0, "MIN_ROOM_R": 2.0, "PD_REQUIRED": False, "ZONE_FRESH_REQUIRED": False,
               "SL_WIDEN_TO_STOPS_LEVEL": True,
               "MAX_POSITIONS": 0,                 # 0 = unlimited (book.max_slots)
               "NO_REENTRY_AFTER_LOSS": False,     # a cap on trades, not a quality gate
               "ONE_TRADE_PER_H4_ZONE": False},    # same
}

# ── Kronos (David 2026-10-26: "run this llm and take the trade and show in the dashboard") ──
# Kronos-base (NeoQuasar, the largest public Kronos) forecasts the next HORIZON M15 bars as PATHS sampled paths; the
# GPU side is kronos/signals.py (service kronos-signals, ~/opt/kronos-venv), the trades are engine/kronos_book.py.
# A trade: ≥ P_MIN of the paths end on one side of the last close and the median move is ≥ MIN_MOVE_SPREAD_X spreads
# → market order at the minimum lot, SL SL_ATR × ATR(14, M15), TP TP_ATR × ATR,
# closed after HOLD_BARS bars if neither is hit. Its own magic: V5's book never sees these positions.
# Out-of-sample test before going live (kronos/evaluate.py, GOLD M15 Sep 2025 → Oct 2026): direction right 48.5 %.
# control.json "kronos" (python3 -m engine.run kronos on|off, or the /kronos page) overrides ENABLED; orders also
# need trading ON (control.json "trading") like V5's.
KRONOS = {
    "ENABLED": True,
    # David 2026-10-26 "why only three": the engine's 17 forex pairs + gold + the two big coins. FxPro's other coins
    # are left out: their spread is 0.6-3 × ATR(M15) (median, Sep 2025 → Oct 2026) and MAX_SPREAD_SL allows 0.45 ×,
    # so they could never trade and would only cost GPU time (16 paths ≈ 10-20 s per symbol per bar)
    # David 2026-11-08 "add all the crypto symbols": every FxPro coin on the S&D list is forecast too; most still cannot
    # trade (MAX_SPREAD_SL refuses a spread over 30 % of the 1-ATR stop) — they show on /kronos with the reason
    "SYMBOLS": ["GOLD", "BITCOIN", "ETHEREUM", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
                "EURGBP", "EURJPY", "EURCHF", "EURCAD", "GBPJPY", "GBPCHF", "GBPCAD", "CADJPY", "CADCHF", "CHFJPY",
                "AAVE", "ALGORAND", "APTOS", "AVALANCHE", "BAT", "BINANCECOIN", "BITCOINCASH", "CARDANO", "CHAINLINK",
                "COSMOS", "DASH", "DOGECOIN", "ETHCLASSIC", "FILECOIN", "GRAPH", "HEDERA", "HYPERLIQUID", "IMMUTABLE",
                "INTERNET", "IOTA", "LITECOIN", "NEAR", "NEO", "POLKADOT", "SOLANA", "STELLAR", "SUSHISWAP", "TEZOS",
                "THETA", "TRON", "TRUMP", "UNISWAP", "VECHAIN", "XRP"],
    "MAGIC": 5050600,
    "TF": "M15", "CONTEXT": 512, "HORIZON": 8, "PATHS": 16,
    "P_MIN": 0.75, "MIN_MOVE_SPREAD_X": 2.0,
    # David 2026-10-27 (162 live trades −$8.48, 47 % won: the stop 1.5 ATR was bigger than the target = the median,
    # mostly < 1 ATR): target twice the stop. The 14-month replay (1,740 GOLD/EURUSD/BITCOIN forecasts) loses about the
    # spread with every size (SL 1.5/TP median −0.076 ATR a trade, SL 1/TP 2 −0.065, 38 % won): fewer wins, not an edge
    "ATR_PERIOD": 14, "SL_ATR": 1.0, "TP_ATR": 2.0, "MAX_SPREAD_SL": 0.3,
    # David 2026-11-09 "stoploss under 2 dollar" (a GOLD stop at 1 ATR was ~$10 at 0.01 lot): the stop is pulled in so
    # it never loses more than MAX_RISK_USD at the lot traded; the target stays TP_ATR × ATR. 0 = no cap.
    # Replay of the 231 closed trades before this: now +$1.42, with the $2 stop −$16.60 (9 of 11 gold trades stopped)
    "MAX_RISK_USD": 2.0,
    # David 2026-11-11 "profit should not be below the 1:2 range, it could be more": the target is never under
    # MIN_RR × the stop — checked before the order and again on the real fill (kronos_book.recheck)
    "MIN_RR": 2.0,
    # David 2026-10-26 "make it unlimited, it's just a testing": 0 = no cap — every forecast that passes is its own
    # trade, also on a symbol that already has a Kronos trade open (FxPro demo is a hedging account)
    "HOLD_BARS": 8, "MAX_POSITIONS": 0, "MAX_PER_SYMBOL": 0,
    "MIN_FREE_MARGIN_PCT": 30,           # the one guard left: no new Kronos trade below 30 % free margin (V5 needs it too)
    "SIGNAL_MAX_AGE_SEC": 600,           # act on a forecast only within 10 min of its bar's close
    "FRIDAY_LAST_ENTRY_UTC": "19:30",    # forex / gold: no entry later on a Friday (the 2 h hold would cross the weekly close)
    # David 2026-10-27 "instead of v5 engine take the trade in MT5 ... check with kronos": Claude's own trades, placed with
    # the mt5 tools (mt5_mcp.py, MT5_MCP_MAGIC), are shown on /kronos next to Kronos' — read only, never managed here
    "CLAUDE_MAGIC": 24102099,
    "DIR": os.path.join(DATA_DIR, "kronos"),
}

# ── DAVID's supply / demand, traded (David 2026-11-05: "take the trade in the 15m, start the trading") ──
# engine/sdd_book.py: every valid S&D David zone (engine/sd_david.py, the class video 6 rule) on M15 that is still
# FRESH gets a LIMIT order at its entry (candle A's wick), stop beyond candle A, target T1 (Fib 0.618 from the entry
# to the recent high / low), minimum lot. The order is cancelled when the zone ends (broken / CHoCH against it) or
# is touched without a fill. David's choices 2026-11-05: auto-trade every zone, target T1, every symbol (crypto + forex + gold).
# NOT backtested before going live (the earlier S&D rules backtested had no edge). control.json "sdd" overrides
# ENABLED (python3 -m engine.run sdd on|off|status); orders also need trading ON like V5's.
SDD = {
    "ENABLED": True,
    # David 2026-11-05 (2nd ask): every symbol on the /smc list = the engine's crypto + forex + gold (was forex + gold)
    "SYMBOLS": "all", "SYMBOLS_EXTRA": ["GOLD"],
    "MAGIC": 5050700,
    "TF": "M15", "BARS": 3000,           # the same window as the /smc chart, so the zones are the ones David sees
    "TARGET": 1,                         # T1 = Fib 0.618
    "MAX_SPREAD_RISK": 0.25,             # skip a zone whose spread is over 25 % of its stop distance
    # David 2026-11-09: "make the stop loss 10 points below the demand zone or 10 points above the supply zone"
    # (MT5 points = the symbol's point: 0.00001 on EURUSD = 1 pip for 10, 0.01 on GOLD / BITCOIN). Waiting orders move too
    "SL_BUFFER_POINTS": 10,
    "MIN_FREE_MARGIN_PCT": 30,
    "DIR": os.path.join(DATA_DIR, "sdd"),
}

# ── S&D David with LAYER entries (class video 6 [28:01–31:52], David 2026-11-12: "implement this into the live and we
# have to track this vs now normal tp") — engine/sdd_layers.py. The SAME zones as S&D David (its bars and zones are
# shared), traded a second way on its own magic so the two can be compared zone by zone (/api/sdd/compare):
#   L1 limit at the FVG's near edge (first touch), L2 at candle A's wick (= the normal S&D entry), L3 at A's 50 % line;
#   one stop for all, beyond A (as S&D David); targets measured from L1 to the leg's extreme (the Fib 0 = the class's
#   "overall target"): L1 → 50 %, L2 → 75 %, L3 → 100 %. When one layer takes its target the waiting layers of that
#   zone are cancelled and the open ones go to break-even; after the second target the last one's stop goes to TP1.
#   Minimum lot per layer (0.01 can't be split): a full fill risks up to 3 × one S&D trade.
# python3 -m engine.run sdd_layers on|off|status (control.json "sdd_layers"); orders also need trading ON.
SDD_LAYERS = {
    "ENABLED": True,
    "MAGIC": 5050710,
    "TP_FRACS": [0.5, 0.75, 1.0],        # L1, L2, L3: how far from L1 to the leg's extreme each layer's target sits
    # FxPro demo: at most 70 PENDING orders on the account (limit_orders; positions don't count). On day one the layers
    # took every free slot (40) and the broker refused the rest with 10033 — S&D David and Fib would have been next. The
    # layers keep RESERVE slots free for the others and use what is left on the zones nearest to price.
    "ORDER_LIMIT": 70, "RESERVE": 15,
    "DIR": os.path.join(DATA_DIR, "sdd_layers"),
}

# ── the class's Fib rules (class video 5, David 2026-11-12: "go with trend and fib retracement ... add that next to
# the S&D David", then "now update these strategies to the live") — engine/fib_trend.py (rules), engine/fib_reject.py
# (the LIVE versions + their reject checklist), engine/fib_book.py (orders), /smc layers "Fib trend" / "Fib retr.".
# As taught, both rules lost (backtest 18 pairs + gold: −0.2 R / trade after the spread). Live are the two versions
# that stopped losing on 2023–2026 data never used to choose them (engine/research/fib_trend/reject.py):
#   retrace  every BOS leg: LIMIT at 0.382, stop 0.1 ATR under the swing low, target 2R; rejected on 2+ warnings
#            (+0.02 R / trade kept, 6,080 trades, t 1.1)
#   trend    entry as taught (a STOP at the high / low of the candle that touched 0.618, for the next candle only), stop
#            0.1 ATR under the swing low, target 2R; rejected on any warning (+0.04 R, 1,446 trades, t 1.1)
# on 1 h and 4 h (2 h was in the test; the engine has no 2 h feed), forex + gold. Small, unproven edges: demo, minimum lot.
# python3 -m engine.run fib on|off|status (control.json "fib"); orders also need trading ON.
FIB = {
    "ENABLED": True,
    "RULES": [{"id": "retrace-H1", "rule": "retrace", "tf": "H1"}, {"id": "retrace-H4", "rule": "retrace", "tf": "H4"},
              {"id": "trend-H1", "rule": "trend", "tf": "H1"}, {"id": "trend-H4", "rule": "trend", "tf": "H4"}],
    "SYMBOLS": ["GOLD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY",
                "EURGBP", "EURCHF", "EURCAD", "GBPCHF", "GBPCAD", "CADCHF", "CADJPY", "CHFJPY"],
    "MAGIC": 5050800,
    "BARS": 3000,
    "MIN_FREE_MARGIN_PCT": 30,
    "DIR": os.path.join(DATA_DIR, "fib"),
}

# ── Kronos × S&D David zones (David 2026-11-07: "run the kronos for 50 candles ... will it touch the BOS supply /
# demand FVG zone ... not the 2 h one, check the 15m, all the candles, show in the dashboard") ──
# concepter/kronos/zone_touch.py (GPU, service kronos-zones): for every symbol with a FRESH S&D David zone, Kronos-base
# draws PATHS paths of the next HORIZON M15 bars (each path with its own high / low) and counts the paths that touch
# the zone's wick (entry), its 50 % line, and close beyond its stop. Read-only: no orders. Page /kzones.
# ~57 s per symbol on the GTX 1650 (16 paths × 50 bars), so a full pass is long: nearest zones are forecast first.
KRONOS_ZONES = {
    "TF": "M15", "HORIZON": 50, "PATHS": 16, "CONTEXT": 512, "BARS": 3000,
    "DIR": os.path.join(DATA_DIR, "kronos", "zones"),
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
