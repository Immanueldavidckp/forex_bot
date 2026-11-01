# Concept: the Claude engine (new)

A language model (Claude; GPT and Gemini plug in the same way) reads the chart and reports what it sees. It does
not trade: strategies decide what to do with its signals.

It is given David's structure, already computed by the toolkit (`engine/major_structure.py`), the live supply /
demand zones, and the last bars. Its job is to **judge** that structure the way David does, not to invent its own.

## Signals it reports
- **bos**: a candle CLOSED beyond the protected structure level in the trend's direction.
  - `level` = the broken price
  - `origin` = where the breaking move started (the low of a buy move, the high of a sell move)
  - `at` = the break candle
- **choch**: a candle CLOSED beyond the protected swing AGAINST the trend; the trend turns. Same numbers as a BOS.
- **direction**: where the structure points now: buy in an uptrend (higher highs and higher lows that hold), sell in
  a downtrend.
- **setup**: built by the engine from a BOS that passed the check, never taken from the model's answer:
  1. the BOS;
  2. the **supply / demand zone that started its move**: the valid origin zone of that break
     (`engine/supply_demand.py`, `setup.zone_roles`), still fresh (`setup.zone_status`). Demand for a buy BOS,
     supply for a sell BOS;
  3. the **leg's extreme**: the highest high (buy) or lowest low (sell) since the break. It counts once
     `setup.leg_confirm_bars` closed bars made no new extreme, which means the pullback has begun;
  4. no CHoCH or BOS against it since the break, and the BOS at most `setup.max_bos_age_bars` bars old.

  It is reported on the bar the leg is confirmed, with: `entry` (the zone's body edge), `proximal`, `distal`
  (the zone's far edge), `top`, `bottom`, `leg_extreme`, `bos_level`, `origin`, `zone_score`, `rr_to_extreme`.

## David's structure rule (judge every break by it)
- Only two levels exist at any time:
  - the **BOS level** = the leg's extreme, once a real pullback has confirmed it;
  - the **protected** level = the swing that started the last BOS.
- A break is a **close** beyond the level by at least `check.margin_atr` × ATR(14). A wick through without a
  close is a sweep, not a break.
- Highs and lows made inside a pullback are **internal**. Breaking them is never a BOS.
- A pullback only counts if price came back at least `check.pullback_atr` × ATR(14) from the extreme.

## Do not report
- A break whose candle did not close beyond the level. The engine checks this against the bars and drops it.
- Internal breaks inside a pullback.
- Anything you are unsure of. Report nothing instead.
