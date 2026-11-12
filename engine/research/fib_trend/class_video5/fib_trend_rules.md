# Fib rules: the class (video 5)

Source: `~/videos/trading/part 5.mp4` (2 h 46 m, TradingView, gold 1 h / 2 h). Spoken in Tamil and translated to English
by Whisper medium on the GTX 1650 → `part5_tx_*.txt`. The file names give the start second: `a_0000` covers 0–11 min,
`a2_0660` 11–44, `b_2640` 44–100, `c_6000` 100–166. Times like `[1:09:30]` point into those files. Key frames are in `hi/`
(rotated): `t2850.jpg` = the 8-rule slide, `t4200.jpg` = his trade, `t7080.jpg` = the swing-count slide.

Code: `engine/fib_trend.py` (both rules), `engine/fib_book.py` (orders, magic 5050800, **off**), `/smc` layers
**Fib trend** / **Fib retr.** next to S&D David, backtest `engine/research/fib_trend/backtest.py` → `results.json`.

## His Fib template `[7:45–8:41]`
The levels are 0, 0.236 (red: "our stop loss zone"), 0.382, 0.5, 0.618 ("golden zone, where we trade"), 0.786, 1 and 1.618.
2.618, 3.618 and 4.236 are switched off.

## Rule 1: FIB GO WITH TREND (the 8-point slide, `[47:00]`)
1. **Trend need to change.** A CHoCH, the "market structure shift" `[48:18]`. A break needs a candle **body close** `[1:00:07]`.
2. **EMA should intercross.** EMA 9 and EMA 21 on the close `[1:01:14–1:01:24]` cross the new way at the trend change.
3. **1 swing need to complete.** "One swing means one break of structure: after the character changes, one BOS needs to
   complete" `[49:31–49:35]`.
4. **Take a trade in the next swing.** That is the 2nd swing from the CHoCH, **and only that one**. A student asked if a
   missed 2nd swing can be taken in the 3rd: "No bro, we shouldn't do that" `[1:13:04–1:13:40]`.
5. **EMA should not intercross.** "After the first intercross, till we take a trade, intercross should not happen" `[52:17]`.
   "After the character change it should not be inter-crossed" `[1:15:13]`. A cross back = "the trend will change" `[54:13]`.
   He says this is why you miss the entry "80 % of the time" `[1:24:59]`.
6. **Implement Fib.** Not the usual "swing high to previous low": draw it "from the swing high to the **current running** low"
   `[50:41–50:49]`. Drag the 0 down while the market still makes new lows, then fix it once it turns `[53:40–53:50, 1:07:01]`.
7. **0.618 need to touch.** A candle touches 0.618 from below, with its body or its wick `[55:18, 56:01–56:06]`.
8. **Take the trade in the next candle once it crosses the 0.618 candle.** Mark the touch candle's **high**. The next candle
   going through it is the entry. If the touch candle closed at its high, the next candle opens there, so enter at once. If the
   next candle doesn't reach it, wait for the next candle that touches 0.618 `[56:10–58:29, 1:07:29–1:07:57]`.
- **Stop:** below 0.236, "push it a little" `[58:43–58:49, 1:09:30]`. Code: 0.236 − 0.1 ATR. In his trade it was 0.93 under, about 0.1 ATR on 2 h gold.
- **Target:** 1.618 `[1:08:05]`.
- **RR:** at least 1 : 1, or no entry `[1:09:44–1:09:50, 1:18:47–1:18:57]`.
- **Markets / timeframes:** 15 min and up; 1 h, 2 h and 4 h are best `[49:41–49:58]`. Forex and gold, not crypto `[1:13:44–1:13:52]`.
  Avoid news `[1:27:04]`. "You won't get regular entries" `[50:54]`, "maybe 2 trades a month" on high timeframes `[1:26:20]`.
- **His trade** (2 h gold, 28 Aug 2025, `t4200.jpg`): 0 = 3373.77, 1 = 3393.69, entry 3386.94, stop 3377.47, target 3406.06, RR 2.03.
  **The code finds the same swing on FxPro's bars:** 1 = 3394.11, 0 = 3373.81, stop **3377.47** (exactly his), target
  3406.66, a win. This is `engine/test_fib_trend.py::test_his_class_trade_28_aug_2025`.

## Rule 2: FIB RETRACEMENT ("the easy one, regular entries", `[1:32:05]`)
- **The Fib:** at a BOS, draw from the swing high (1) to the **previous swing low** (0), meaning the low that the BOS leg started
  from `[1:33:01–1:33:14, 1:41:35–1:42:49]`. If price makes a new high before the entry, **move the high and keep the low**
  `[1:43:05–1:43:37]`.
- **Entry:** 0.618 (a limit order). **Stop:** exactly 0.236. **Target:** 1. That makes it 1 : 1 `[1:36:32–1:37:34]`.
- **Timeframes:** 5 min to 4 h, best 15 / 30 min `[1:38:05–1:38:13]`.
- **Which swings** (slide at `[1:58:00]`, the "safety side"). After a CHoCH:
  - swing 1 is the confirmation swing: no trade
  - swings 2 and 3: trade
  - swing 4: no trade ("a chance of a character change")
  - swing 5 is a confirmation swing again
  - swing 6: trade

  Experienced traders take every BOS `[1:58:24–2:02:31]`.
- He also teaches "layer entries" (splitting the lot between 0.618, 0.5 and 0.382) from `[2:02:50]`. This is **not built.**

## How the code reads "structure"
David's `major_structure.py` (3-ATR pullbacks, levels kept for months) does **not** see the teacher's swings. In August
2025 it had no CHoCH or BOS on 2 h gold. So the Fib rules use their own plain swing structure (`fib_trend.swing_structure`):
- the last pivot high or low (4 candles each side) is the level
- a candle close beyond it is a break
- a break with the trend is a BOS; a break against it is a CHoCH

The class's own definition (`[11:43–13:40, 41:59–43:01]`): "swing and break of structure are the same"; a break needs a
body close ("the wick should not be touched"); a pullback of 2–3 candles is not a structure. Pivot 3 and pivot 4 both reproduce his trade to the cent. Pivot 4 is the default. It was **not** chosen on results:
3, 4 and 5 all lose about the same.

## Backtest (2026-11-12, 18 forex pairs + gold, FxPro history, 6+ years; spread taken off every trade)
| rule | tf | trades | won | R / trade before costs | R / trade after spread |
|---|---|---|---|---|---|
| go with trend | H1 | 3,986 | 33.3 % | −0.13 | −0.23 |
| go with trend | H2 | 2,146 | 33.3 % | −0.11 | −0.20 |
| go with trend | H4 | 3,980 | 33.2 % | −0.14 | −0.21 |
| retracement (safety) | M15 | 34,598 | 47.3 % | −0.05 | −0.26 |
| retracement (safety) | M30 | 34,287 | 47.3 % | −0.04 | −0.21 |
| retracement (safety) | H1 | 16,833 | 48.3 % | +0.00 | −0.11 |
| retracement (safety) | H4 | 15,442 | 50.2 % | +0.03 | −0.04 |
| retracement (every BOS) | H4 | 20,143 | 50.5 % | +0.04 | −0.03 |

- **Go with trend** wins a third of the time at an average RR of 1.7. Break-even needs about 37 %.
- **Optimistic check:** suppose a stop hit inside the entry candle only counts if that candle *closes* beyond the stop. Go with
  trend H2 + H4 then improves to −0.06 R before costs and −0.14 R after. It is still negative.
- **Retracement** is a coin flip at 1 : 1 before costs. The spread decides the result, so small timeframes lose the most.
- **Result: no edge in either rule.** This is the same finding as the earlier S&D tests. That is why `FIB["ENABLED"]` is False.

## Why it loses, and what is LIVE (2026-11-12)
Studies: `engine/research/fib_trend/improve.py` (every trade rebuilt on 30-min candles, 20 changed versions) and
`reject.py` (a reject checklist chosen on 2018–2022, judged on 2023–2026).
- The entry has no edge: Go With Trend trades reach +1R 46.8 % of the time (a coin flip: 50 %). The spread costs
  0.05–0.18 R on these small stops. A 2R target is simply hit less often. The 0.236 stop sits inside the pullback's noise.
- No change of entry / stop / target alone makes either rule profitable in both halves of the history.
- A reject checklist does save loss: in all six versions tested, the rejected trades did worse than the kept ones on the
  unseen 2023–2026 half. Waiting for a rejection candle at the Fib level did not help.

**Live on the demo since 2026-11-12** (`engine/fib_reject.py`, `engine/fib_book.py`, config `FIB`, magic 5050800,
0.01 lot, 1 h + 4 h, 18 forex pairs + gold):
| | Retracement | Go With Trend |
|---|---|---|
| entry | limit at 0.382 of the BOS leg, every BOS | as taught: next candle through the 0.618 candle's high |
| stop | 0.1 ATR under the swing low (Fib 0) | the same |
| target | 2R | 2R |
| rejected when | 2 or more warnings | any warning |
| warnings | CADCHF / EURCAD / GBPCHF; New York session; spread over 15.6 % of the stop; entry in the top 17 % of the 100-candle range; swing ≤ 2.65 ATR; price over 1.58 ATR past EMA 21; swing 4 | CADCHF / GBPCAD / EURCHF / EURCAD / USDCAD; Asia or late (21–24 UTC) session; Tuesday; spread over 10.8 % of the stop |
| 2023–2026, kept | 6,080 trades, +0.02 R / trade after spread (t 1.1) | 1,446 trades, +0.04 R (t 1.1) |
| 2023–2026, rejected | 3,376 trades, −0.04 R | 2,776 trades, −0.11 R |

These are small, unproven edges ("stopped losing"). Some warnings are probably noise (Tuesday, USDCAD, New York): they
are kept because the tested filter is exactly this set. Differences live vs test: the test had 2 h too and built 4 h
candles on UTC hours; the engine uses the broker's 4 h candles.

## Open questions for David
- a) After ~300 live trades: compare with the backtest, keep or stop.
- b) A 2 h feed for the engine (the class's favourite timeframe)?
- d) Layer entries (the lot split across 0.618 / 0.5 / 0.382): build it?
