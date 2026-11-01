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
