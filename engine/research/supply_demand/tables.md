# sd_test.py results (2026-10-30)

zones 46906, controls 139632, shuffled-series zones 52216; horizon 200 bars, max wait 3000, min departure 1.0 h, in-sample = first 70 % of bars

## Overview — v5 zones

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL FX+GOLD v5 | 20399 | 58.2 | 57.9 | +0.2 [-0.6, +1.0] | 56.7 | 54.5 | 54.8 | 44.9 | 44.6 | 5 | 1.43 | 55.5 |
| FX+GOLD v5 M15 | 16280 | 57.7 | 57.9 | -0.2 [-1.0, +0.7] | 56.3 | 54.2 | 54.8 | 44.6 | 44.6 | 5 | 1.43 | 55.9 |
| FX+GOLD v5 H1 | 4119 | 59.9 | 58.1 | +1.8 [+0.1, +3.5] | 58.2 | 56.0 | 54.9 | 46.3 | 44.7 | 5 | 1.44 | 54.1 |
| GOLD M15 v5 | 3223 | 57.1 | 57.2 | -0.1 [-2.1, +1.9] | 55.9 | 53.7 | 54.2 | 44.8 | 44.5 | 6 | 1.43 | 55.8 |
| GOLD H1 v5 | 827 | 56.5 | 55.6 | +0.8 [-3.0, +4.8] | 58.3 | 50.4 | 51.6 | 43.4 | 42.2 | 6 | 1.46 | 57.3 |
| EURUSD M15 v5 | 3270 | 58.0 | 57.5 | +0.5 [-1.4, +2.5] | 56.3 | 54.1 | 54.7 | 44.2 | 43.7 | 5 | 1.41 | 56.6 |
| EURUSD H1 v5 | 828 | 57.6 | 57.3 | +0.3 [-3.7, +4.1] | 57.2 | 54.6 | 55.3 | 43.7 | 44.9 | 6 | 1.47 | 56.6 |
| GBPUSD M15 v5 | 3313 | 58.2 | 58.3 | -0.1 [-2.1, +1.7] | 57.2 | 54.7 | 55.3 | 45.4 | 45.2 | 5 | 1.40 | 55.1 |
| GBPUSD H1 v5 | 825 | 62.1 | 58.7 | +3.4 [-0.4, +7.2] | 56.8 | 60.6 | 56.7 | 50.3 | 44.7 | 5 | 1.38 | 49.8 |
| USDJPY M15 v5 | 3284 | 58.5 | 57.1 | +1.4 [-0.5, +3.5] | 56.1 | 55.1 | 53.7 | 45.1 | 43.6 | 5 | 1.47 | 55.4 |
| USDJPY H1 v5 | 829 | 62.4 | 57.2 | +5.2 [+1.4, +9.0] | 58.0 | 58.0 | 52.5 | 47.2 | 44.2 | 4 | 1.46 | 53.0 |
| AUDUSD M15 v5 | 3190 | 56.7 | 59.5 | -2.7 [-4.7, -0.8] | 56.1 | 53.2 | 56.0 | 43.4 | 46.1 | 5 | 1.45 | 56.8 |
| AUDUSD H1 v5 | 810 | 61.0 | 61.7 | -0.7 [-4.6, +3.3] | 60.5 | 56.4 | 58.3 | 47.0 | 47.6 | 5 | 1.39 | 53.6 |
| BITCOIN M15 v5 | 3324 | 58.0 | 58.2 | -0.1 [-2.1, +1.8] | 56.5 | 53.4 | 54.8 | 44.0 | 45.1 | 6 | 1.49 | 56.6 |
| BITCOIN H1 v5 | 812 | 58.1 | 59.0 | -0.9 [-4.8, +3.0] | 62.0 | 53.1 | 56.1 | 44.3 | 46.1 | 6 | 1.54 | 56.5 |

### In-sample / out-of-sample — v5

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX+GOLD v5 IS | 14396 | 58.2 | 58.1 | +0.2 [-0.7, +1.1] | 56.5 | 54.6 | 54.8 | 45.1 | 44.6 | 5 | 1.43 | 55.4 |
| FX+GOLD v5 M15 IS | 11480 | 57.8 | 58.0 | -0.3 [-1.3, +0.8] | 56.0 | 54.2 | 54.8 | 44.7 | 44.5 | 5 | 1.43 | 55.8 |
| FX+GOLD v5 H1 IS | 2916 | 60.2 | 58.3 | +1.9 [-0.1, +4.0] | 58.5 | 56.4 | 54.8 | 46.7 | 44.8 | 6 | 1.44 | 53.9 |
| FX+GOLD v5 OOS | 6003 | 58.0 | 57.6 | +0.4 [-1.1, +1.8] | 57.2 | 54.4 | 54.8 | 44.6 | 44.7 | 5 | 1.44 | 55.8 |
| FX+GOLD v5 M15 OOS | 4800 | 57.6 | 57.6 | +0.0 [-1.6, +1.6] | 57.1 | 54.2 | 54.8 | 44.4 | 44.8 | 5 | 1.44 | 56.1 |
| FX+GOLD v5 H1 OOS | 1203 | 59.3 | 57.5 | +1.8 [-1.5, +4.9] | 57.5 | 55.1 | 55.0 | 45.4 | 44.4 | 5 | 1.44 | 54.4 |

### Base type — v5

### Freshness — v5 (first vs second return, FX+GOLD)

| set | first return hold % | zones that held then returned | second return hold % |
|---|---|---|---|
| v5 M15 | 57.7 | 9191 | 58.0 |
| v5 H1 | 59.9 | 2405 | 59.4 |
| v5 GOLD M15 | 57.1 | 1790 | 56.9 |
| v5 GOLD H1 | 56.5 | 444 | 60.4 |
| v5 EURUSD M15 | 58.0 | 1851 | 56.8 |
| v5 EURUSD H1 | 57.6 | 468 | 57.7 |
| v5 GBPUSD M15 | 58.2 | 1884 | 58.3 |
| v5 GBPUSD H1 | 62.1 | 506 | 58.9 |
| v5 USDJPY M15 | 58.5 | 1891 | 59.0 |
| v5 USDJPY H1 | 62.4 | 507 | 59.2 |
| v5 AUDUSD M15 | 56.7 | 1775 | 58.9 |
| v5 AUDUSD H1 | 61.0 | 480 | 61.0 |
| v5 BITCOIN M15 | 58.0 | 1882 | 56.5 |
| v5 BITCOIN H1 | 58.1 | 465 | 52.7 |

### Hold rate by age / height / departure — v5 FX+GOLD (zones vs matched controls)

| bars to return | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-10 | 12804 | 57.8 | 36345 | 58.2 | -0.4 |
| 10-30 | 3461 | 59.5 | 11128 | 59.1 | +0.5 |
| 30-100 | 2111 | 59.8 | 6853 | 57.9 | +1.9 |
| 100-300 | 1087 | 56.2 | 3279 | 55.1 | +1.1 |
| 300-3001 | 936 | 56.8 | 2826 | 53.6 | +3.2 |

| height / ATR | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 0-0.5 | 2497 | 55.3 | 7489 | 55.8 | -0.5 |
| 0.5-1 | 12753 | 58.5 | 38084 | 58.4 | +0.2 |
| 1-2 | 5054 | 58.4 | 14610 | 58.0 | +0.5 |
| 2-100 | 95 | 66.3 | 248 | 55.2 | +11.1 |

| departure / height | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-2 | 7459 | 57.8 | 20292 | 58.0 | -0.1 |
| 2-3 | 3959 | 59.1 | 12496 | 59.0 | +0.1 |
| 3-5 | 3617 | 58.7 | 11626 | 58.3 | +0.3 |
| 5-10 | 2865 | 58.2 | 8771 | 58.5 | -0.3 |
| 10-1000 | 2499 | 56.9 | 7246 | 54.7 | +2.3 |

### Criteria — v5 M15, FX+GOLD pooled (hold = 1 zone height before a close beyond distal)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1611 | 57.7 | 57.7 | -0.1 | 0.981 | +0.3 | -1.2 |
| major BOS before the return (any delay) | 2552 | 57.2 | 57.8 | -0.6 | 0.611 | -0.4 | -0.9 |
| zone inside any major break's move | 2590 | 57.4 | 57.8 | -0.4 | 0.749 | -0.1 | -1.2 |
| the break is a CHoCH | 561 | 59.0 | 57.7 | +1.3 | 0.538 | +1.4 | +1.1 |
| BOS gate (3-bar fractal swing) | 7697 | 57.2 | 58.2 | -1.0 | 0.205 | -0.6 | -1.8 |
| displacement >= 2 x avg body | 11417 | 57.5 | 58.2 | -0.6 | 0.474 | -0.8 | -0.2 |
| displacement >= 3 x avg body | 5377 | 56.9 | 58.1 | -1.2 | 0.152 | -1.1 | -1.5 |
| FVG in the leg-out | 12639 | 58.0 | 56.7 | +1.3 | 0.161 | +2.8 | -2.1 |
| FVG >= 0.3 ATR | 8431 | 58.0 | 57.4 | +0.7 | 0.385 | +1.3 | -0.8 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 5790 | 57.9 | 57.6 | +0.3 | 0.729 | +1.0 | -1.4 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 12777 | 57.9 | 57.1 | +0.8 | 0.421 | +0.8 | +0.7 |
| base >= 3 candles | 3503 | 57.1 | 57.9 | -0.8 | 0.433 | -0.8 | -0.7 |
| departure >= 3 zone heights before the return | 7121 | 57.6 | 57.8 | -0.2 | 0.847 | -0.5 | +0.5 |
| departure >= 2 ATR before the return | 8484 | 58.2 | 57.2 | +1.1 | 0.170 | +1.7 | -0.5 |
| leg-out candle range >= 2 zone heights | 7403 | 56.9 | 58.4 | -1.6 | 0.044 | -2.2 | -0.1 |
| zone height <= 0.5 ATR | 1882 | 54.4 | 58.2 | -3.8 | 0.002 | -5.2 | -0.8 |
| zone height > 1 ATR | 4109 | 59.0 | 57.3 | +1.7 | 0.062 | +2.6 | -0.5 |
| with the major trend | 8165 | 57.7 | 57.8 | -0.1 | 0.936 | -0.3 | +0.5 |
| against the major trend | 8101 | 57.8 | 57.7 | +0.1 | 0.899 | +0.3 | -0.5 |
| demand in discount / supply in premium (major range) | 8217 | 58.3 | 57.1 | +1.2 | 0.119 | +1.2 | +1.1 |
| ... of the last 100 bars' range | 8319 | 58.6 | 56.8 | +1.8 | 0.017 | +1.6 | +2.3 |
| liquidity sweep just before the leg-out | 3616 | 59.6 | 57.2 | +2.4 | 0.008 | +2.5 | +2.2 |
| round-number level in / at the zone | 3294 | 59.0 | 57.4 | +1.6 | 0.097 | +1.7 | +1.3 |
| RR >= 2 to the nearest live opposing zone | 9683 | 58.0 | 57.3 | +0.7 | 0.365 | +1.4 | -1.0 |
| no live opposing zone above / below | 387 | 56.3 | 57.8 | -1.4 | 0.604 | -2.4 | +3.7 |
| returned within 50 bars | 13867 | 57.9 | 56.6 | +1.4 | 0.211 | +0.5 | +3.4 |
| returned after > 200 bars | 987 | 55.9 | 57.8 | -1.9 | 0.252 | -2.0 | -1.8 |
| formed in Asia (00-07 UTC) | 5101 | 58.0 | 57.6 | +0.4 | 0.680 | -0.7 | +2.8 |
| formed in London (07-12 UTC) | 3362 | 59.0 | 57.4 | +1.7 | 0.085 | +1.6 | +1.9 |
| formed in London/NY overlap (12-16 UTC) | 2781 | 58.2 | 57.6 | +0.6 | 0.550 | +1.2 | -1.0 |
| BOS gate + FVG | 1465 | 57.7 | 57.7 | -0.0 | 0.979 | +0.1 | -0.4 |
| BOS gate + FVG kept | 960 | 57.6 | 57.7 | -0.1 | 0.948 | -0.7 | +1.4 |
| BOS gate + with trend | 1046 | 57.1 | 57.8 | -0.7 | 0.662 | -0.1 | -2.3 |
| BOS gate + discount/premium | 179 | 57.5 | 57.7 | -0.2 | 1.000 | -1.4 | +3.3 |
| BOS gate + sweep | 238 | 60.9 | 57.7 | +3.3 | 0.316 | +2.2 | +6.7 |
| BOS gate + FVG + with trend | 949 | 56.6 | 57.8 | -1.2 | 0.468 | -0.7 | -2.8 |
| BOS gate + FVG + discount/premium | 175 | 57.1 | 57.7 | -0.6 | 0.879 | -2.1 | +3.8 |
| BOS gate + departure >= 3 h | 1227 | 57.7 | 57.7 | -0.0 | 1.000 | -0.2 | +0.4 |
| fractal BOS + FVG | 6463 | 57.3 | 58.0 | -0.7 | 0.393 | +0.3 | -2.9 |
| FVG + departure >= 3 h | 6531 | 57.7 | 57.7 | -0.0 | 0.987 | -0.1 | +0.1 |
| sweep + FVG | 2899 | 59.2 | 57.4 | +1.8 | 0.076 | +2.7 | -0.5 |
| sweep + major BOS before return | 496 | 57.7 | 57.7 | -0.1 | 1.000 | -0.4 | +0.8 |
| with trend + discount/premium | 2466 | 58.7 | 57.5 | +1.2 | 0.274 | +0.5 | +2.5 |
| NO major BOS (David: invalid) | 14669 | 57.7 | 57.7 | +0.1 | 0.978 | -0.3 | +1.2 |

### Criteria — v5 M15, FX+GOLD pooled, hold = 1 ATR

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1611 | 55.0 | 54.1 | +0.9 | 0.494 | +1.5 | -0.7 |
| major BOS before the return (any delay) | 2552 | 54.3 | 54.1 | +0.2 | 0.876 | +0.2 | +0.2 |
| zone inside any major break's move | 2590 | 54.6 | 54.1 | +0.5 | 0.700 | +0.6 | -0.1 |
| the break is a CHoCH | 561 | 55.8 | 54.1 | +1.7 | 0.435 | +2.2 | +0.1 |
| BOS gate (3-bar fractal swing) | 7697 | 54.2 | 54.1 | +0.1 | 0.899 | +0.2 | -0.1 |
| displacement >= 2 x avg body | 11417 | 54.3 | 53.8 | +0.5 | 0.550 | +0.0 | +1.6 |
| displacement >= 3 x avg body | 5377 | 54.5 | 54.0 | +0.6 | 0.520 | +0.2 | +1.3 |
| FVG in the leg-out | 12639 | 55.0 | 51.2 | +3.8 | <0.001 | +4.2 | +2.7 |
| FVG >= 0.3 ATR | 8431 | 55.1 | 53.2 | +2.0 | 0.009 | +2.3 | +1.1 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 5790 | 55.8 | 53.3 | +2.6 | <0.001 | +2.6 | +2.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 12777 | 53.8 | 55.6 | -1.8 | 0.059 | -2.0 | -1.2 |
| base >= 3 candles | 3503 | 55.6 | 53.8 | +1.8 | 0.059 | +2.0 | +1.2 |
| departure >= 3 zone heights before the return | 7121 | 52.6 | 55.4 | -2.7 | <0.001 | -3.4 | -1.1 |
| departure >= 2 ATR before the return | 8484 | 55.2 | 53.1 | +2.2 | 0.005 | +2.2 | +2.1 |
| leg-out candle range >= 2 zone heights | 7403 | 50.2 | 57.5 | -7.3 | <0.001 | -7.9 | -5.8 |
| zone height <= 0.5 ATR | 1882 | 44.5 | 55.4 | -11.0 | <0.001 | -11.5 | -9.8 |
| zone height > 1 ATR | 4109 | 62.3 | 51.5 | +10.8 | <0.001 | +11.5 | +9.1 |
| with the major trend | 8165 | 53.8 | 54.5 | -0.7 | 0.368 | -1.2 | +0.6 |
| against the major trend | 8101 | 54.6 | 53.8 | +0.8 | 0.327 | +1.3 | -0.6 |
| demand in discount / supply in premium (major range) | 8217 | 55.0 | 53.3 | +1.8 | 0.021 | +1.8 | +1.6 |
| ... of the last 100 bars' range | 8319 | 55.2 | 53.2 | +2.0 | 0.011 | +1.5 | +3.2 |
| liquidity sweep just before the leg-out | 3616 | 57.5 | 53.2 | +4.3 | <0.001 | +4.6 | +3.6 |
| round-number level in / at the zone | 3294 | 57.7 | 53.3 | +4.4 | <0.001 | +4.4 | +4.4 |
| RR >= 2 to the nearest live opposing zone | 9683 | 52.4 | 56.8 | -4.4 | <0.001 | -3.9 | -5.7 |
| no live opposing zone above / below | 387 | 50.1 | 54.3 | -4.1 | 0.112 | -5.1 | +0.6 |
| returned within 50 bars | 13867 | 54.0 | 55.2 | -1.2 | 0.299 | -1.1 | -1.2 |
| returned after > 200 bars | 987 | 53.2 | 54.2 | -1.0 | 0.531 | -1.3 | -0.3 |
| formed in Asia (00-07 UTC) | 5101 | 54.8 | 53.9 | +0.8 | 0.332 | -0.1 | +3.1 |
| formed in London (07-12 UTC) | 3362 | 54.9 | 54.0 | +0.9 | 0.329 | +1.1 | +0.5 |
| formed in London/NY overlap (12-16 UTC) | 2781 | 57.5 | 53.5 | +4.0 | <0.001 | +4.0 | +3.9 |
| BOS gate + FVG | 1465 | 55.5 | 54.0 | +1.4 | 0.294 | +1.9 | +0.0 |
| BOS gate + FVG kept | 960 | 55.7 | 54.1 | +1.6 | 0.327 | +1.2 | +2.9 |
| BOS gate + with trend | 1046 | 54.8 | 54.1 | +0.6 | 0.694 | +1.2 | -1.1 |
| BOS gate + discount/premium | 179 | 54.7 | 54.2 | +0.6 | 0.882 | +1.5 | -2.1 |
| BOS gate + sweep | 238 | 60.1 | 54.1 | +6.0 | 0.077 | +5.8 | +6.6 |
| BOS gate + FVG + with trend | 949 | 54.6 | 54.2 | +0.4 | 0.813 | +0.9 | -0.9 |
| BOS gate + FVG + discount/premium | 175 | 54.9 | 54.2 | +0.7 | 0.879 | +0.8 | +0.3 |
| BOS gate + departure >= 3 h | 1227 | 54.1 | 54.2 | -0.1 | 0.976 | +0.1 | -0.7 |
| fractal BOS + FVG | 6463 | 54.7 | 53.8 | +0.9 | 0.242 | +1.5 | -0.4 |
| FVG + departure >= 3 h | 6531 | 53.0 | 55.0 | -2.0 | 0.011 | -2.8 | +0.1 |
| sweep + FVG | 2899 | 57.8 | 53.4 | +4.4 | <0.001 | +4.9 | +3.0 |
| sweep + major BOS before return | 496 | 56.9 | 54.1 | +2.8 | 0.233 | +1.7 | +6.1 |
| with trend + discount/premium | 2466 | 54.9 | 54.0 | +0.9 | 0.441 | -0.2 | +3.1 |
| NO major BOS (David: invalid) | 14669 | 54.1 | 55.0 | -0.9 | 0.488 | -1.5 | +0.7 |

### Criteria — v5 M15, FX+GOLD pooled, hold = 2 zone heights (RR 2)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1611 | 45.6 | 44.5 | +1.1 | 0.426 | +1.4 | +0.3 |
| major BOS before the return (any delay) | 2552 | 45.9 | 44.3 | +1.6 | 0.138 | +1.5 | +2.0 |
| zone inside any major break's move | 2590 | 46.1 | 44.3 | +1.8 | 0.087 | +1.8 | +1.8 |
| the break is a CHoCH | 561 | 46.0 | 44.5 | +1.5 | 0.513 | +1.5 | +1.3 |
| BOS gate (3-bar fractal swing) | 7697 | 44.4 | 44.7 | -0.4 | 0.634 | -0.7 | +0.5 |
| displacement >= 2 x avg body | 11417 | 44.5 | 44.7 | -0.2 | 0.793 | -0.8 | +1.2 |
| displacement >= 3 x avg body | 5377 | 44.6 | 44.6 | +0.0 | 0.973 | -0.3 | +0.8 |
| FVG in the leg-out | 12639 | 45.0 | 43.0 | +2.0 | 0.034 | +2.4 | +1.1 |
| FVG >= 0.3 ATR | 8431 | 45.2 | 43.9 | +1.3 | 0.110 | +1.1 | +1.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 5790 | 45.6 | 44.0 | +1.6 | 0.047 | +2.4 | -0.4 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 12777 | 44.7 | 44.1 | +0.6 | 0.530 | +0.3 | +1.4 |
| base >= 3 candles | 3503 | 44.1 | 44.7 | -0.6 | 0.537 | -0.3 | -1.4 |
| departure >= 3 zone heights before the return | 7121 | 46.4 | 43.1 | +3.3 | <0.001 | +2.9 | +4.1 |
| departure >= 2 ATR before the return | 8484 | 46.1 | 42.9 | +3.3 | <0.001 | +3.4 | +3.0 |
| leg-out candle range >= 2 zone heights | 7403 | 44.5 | 44.6 | -0.0 | 0.957 | -0.9 | +2.0 |
| zone height <= 0.5 ATR | 1882 | 45.6 | 44.4 | +1.2 | 0.331 | +0.2 | +3.5 |
| zone height > 1 ATR | 4109 | 44.6 | 44.6 | +0.0 | 0.986 | +1.0 | -2.4 |
| with the major trend | 8165 | 44.9 | 44.3 | +0.6 | 0.443 | +0.2 | +1.6 |
| against the major trend | 8101 | 44.3 | 44.8 | -0.6 | 0.478 | -0.1 | -1.6 |
| demand in discount / supply in premium (major range) | 8217 | 45.3 | 43.9 | +1.4 | 0.074 | +0.7 | +2.9 |
| ... of the last 100 bars' range | 8319 | 45.5 | 43.6 | +1.9 | 0.011 | +1.3 | +3.5 |
| liquidity sweep just before the leg-out | 3616 | 46.4 | 44.0 | +2.4 | 0.011 | +3.2 | +0.2 |
| round-number level in / at the zone | 3294 | 44.7 | 44.5 | +0.2 | 0.862 | +0.3 | -0.2 |
| RR >= 2 to the nearest live opposing zone | 9683 | 45.6 | 43.0 | +2.6 | 0.001 | +3.1 | +1.5 |
| no live opposing zone above / below | 387 | 42.1 | 44.6 | -2.5 | 0.346 | -3.5 | +2.4 |
| returned within 50 bars | 13867 | 44.4 | 45.8 | -1.4 | 0.186 | -2.4 | +1.0 |
| returned after > 200 bars | 987 | 45.3 | 44.5 | +0.8 | 0.639 | +0.1 | +2.7 |
| formed in Asia (00-07 UTC) | 5101 | 45.8 | 44.0 | +1.8 | 0.034 | +0.6 | +4.6 |
| formed in London (07-12 UTC) | 3362 | 46.3 | 44.1 | +2.1 | 0.029 | +2.4 | +1.4 |
| formed in London/NY overlap (12-16 UTC) | 2781 | 42.2 | 45.1 | -2.8 | 0.006 | -2.0 | -5.2 |
| BOS gate + FVG | 1465 | 45.9 | 44.4 | +1.5 | 0.262 | +1.4 | +1.8 |
| BOS gate + FVG kept | 960 | 46.0 | 44.5 | +1.6 | 0.352 | +1.5 | +1.6 |
| BOS gate + with trend | 1046 | 45.5 | 44.5 | +1.0 | 0.528 | +1.4 | -0.2 |
| BOS gate + discount/premium | 179 | 43.0 | 44.6 | -1.6 | 0.703 | -2.6 | +1.3 |
| BOS gate + sweep | 238 | 44.1 | 44.6 | -0.5 | 0.892 | -1.8 | +3.9 |
| BOS gate + FVG + with trend | 949 | 45.3 | 44.5 | +0.8 | 0.636 | +1.0 | +0.2 |
| BOS gate + FVG + discount/premium | 175 | 42.9 | 44.6 | -1.7 | 0.710 | -3.5 | +3.4 |
| BOS gate + departure >= 3 h | 1227 | 46.5 | 44.4 | +2.0 | 0.168 | +2.1 | +1.8 |
| fractal BOS + FVG | 6463 | 44.8 | 44.4 | +0.4 | 0.668 | +0.5 | +0.1 |
| FVG + departure >= 3 h | 6531 | 46.5 | 43.3 | +3.3 | <0.001 | +2.7 | +4.7 |
| sweep + FVG | 2899 | 46.3 | 44.2 | +2.1 | 0.039 | +3.1 | -0.6 |
| sweep + major BOS before return | 496 | 43.5 | 44.6 | -1.1 | 0.644 | -1.0 | -1.2 |
| with trend + discount/premium | 2466 | 46.4 | 44.2 | +2.1 | 0.050 | +1.0 | +4.5 |
| NO major BOS (David: invalid) | 14669 | 44.5 | 45.6 | -1.1 | 0.402 | -1.4 | -0.3 |

### Criteria — v5 H1, FX+GOLD pooled (hold = 1 zone height before a close beyond distal)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 466 | 58.8 | 60.0 | -1.2 | 0.609 | -0.4 | -4.1 |
| major BOS before the return (any delay) | 714 | 59.7 | 59.9 | -0.3 | 0.898 | +1.1 | -4.8 |
| zone inside any major break's move | 719 | 59.7 | 59.9 | -0.3 | 0.900 | +1.1 | -4.8 |
| the break is a CHoCH | 171 | 61.4 | 59.8 | +1.6 | 0.691 | +2.8 | -4.5 |
| BOS gate (3-bar fractal swing) | 1957 | 60.2 | 59.6 | +0.6 | 0.732 | +0.3 | +1.3 |
| displacement >= 2 x avg body | 3056 | 60.3 | 58.7 | +1.6 | 0.359 | +4.0 | -4.1 |
| displacement >= 3 x avg body | 1599 | 60.0 | 59.8 | +0.2 | 0.891 | +1.9 | -3.7 |
| FVG in the leg-out | 3055 | 59.9 | 59.9 | +0.0 | 1.000 | -0.2 | +0.4 |
| FVG >= 0.3 ATR | 2024 | 60.0 | 59.8 | +0.3 | 0.869 | +0.2 | +0.4 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1448 | 59.8 | 59.9 | -0.1 | 0.948 | +0.9 | -2.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3308 | 60.9 | 55.9 | +5.0 | 0.010 | +4.8 | +5.6 |
| base >= 3 candles | 811 | 55.9 | 60.9 | -5.0 | 0.011 | -4.8 | -5.6 |
| departure >= 3 zone heights before the return | 1860 | 59.5 | 60.2 | -0.7 | 0.654 | +0.3 | -3.0 |
| departure >= 2 ATR before the return | 2138 | 59.4 | 60.4 | -1.0 | 0.502 | -0.9 | -1.4 |
| leg-out candle range >= 2 zone heights | 2150 | 60.6 | 59.2 | +1.4 | 0.361 | +3.7 | -4.1 |
| zone height <= 0.5 ATR | 617 | 58.3 | 60.2 | -1.8 | 0.401 | -0.8 | -4.4 |
| zone height > 1 ATR | 1035 | 57.1 | 60.8 | -3.7 | 0.032 | -5.5 | +0.6 |
| with the major trend | 2071 | 59.7 | 60.1 | -0.3 | 0.853 | -2.3 | +4.5 |
| against the major trend | 2039 | 60.2 | 59.6 | +0.6 | 0.733 | +2.6 | -4.5 |
| demand in discount / supply in premium (major range) | 2125 | 59.6 | 60.2 | -0.6 | 0.732 | +0.1 | -2.2 |
| ... of the last 100 bars' range | 2119 | 60.1 | 59.7 | +0.5 | 0.788 | +0.7 | +0.1 |
| liquidity sweep just before the leg-out | 848 | 57.9 | 60.4 | -2.5 | 0.182 | -1.2 | -5.9 |
| round-number level in / at the zone | 1439 | 57.5 | 61.2 | -3.7 | 0.021 | -3.3 | -4.8 |
| RR >= 2 to the nearest live opposing zone | 2458 | 60.0 | 59.7 | +0.4 | 0.822 | +1.0 | -1.1 |
| no live opposing zone above / below | 177 | 58.2 | 60.0 | -1.8 | 0.635 | -2.1 | -1.0 |
| returned within 50 bars | 3496 | 59.6 | 61.3 | -1.7 | 0.447 | -4.1 | +5.9 |
| returned after > 200 bars | 249 | 59.8 | 59.9 | -0.1 | 1.000 | +3.2 | -9.8 |
| formed in Asia (00-07 UTC) | 1400 | 61.2 | 59.2 | +2.0 | 0.219 | +0.4 | +5.9 |
| formed in London (07-12 UTC) | 1005 | 58.6 | 60.3 | -1.7 | 0.354 | -0.4 | -4.5 |
| formed in London/NY overlap (12-16 UTC) | 677 | 62.5 | 59.4 | +3.1 | 0.133 | +1.1 | +8.4 |
| BOS gate + FVG | 421 | 58.7 | 60.0 | -1.4 | 0.604 | -0.8 | -3.4 |
| BOS gate + FVG kept | 279 | 60.6 | 59.8 | +0.7 | 0.840 | +0.7 | +0.8 |
| BOS gate + with trend | 289 | 57.8 | 60.1 | -2.3 | 0.460 | -1.8 | -3.7 |
| BOS gate + discount/premium | 59 | 55.9 | 60.0 | -4.0 | 0.593 | -1.5 | -13.3 |
| BOS gate + sweep | 60 | 63.3 | 59.8 | +3.5 | 0.602 | +5.3 | -9.3 |
| BOS gate + FVG + with trend | 258 | 58.1 | 60.0 | -1.9 | 0.557 | -1.9 | -2.0 |
| BOS gate + FVG + discount/premium | 58 | 56.9 | 59.9 | -3.0 | 0.686 | -0.2 | -13.3 |
| BOS gate + departure >= 3 h | 368 | 57.1 | 60.2 | -3.1 | 0.256 | -3.2 | -3.2 |
| fractal BOS + FVG | 1610 | 60.4 | 59.5 | +0.9 | 0.582 | +0.5 | +1.9 |
| FVG + departure >= 3 h | 1668 | 59.7 | 60.1 | -0.4 | 0.798 | +0.6 | -2.9 |
| sweep + FVG | 651 | 58.1 | 60.2 | -2.2 | 0.319 | -1.3 | -4.4 |
| sweep + major BOS before return | 128 | 55.5 | 60.0 | -4.6 | 0.317 | -2.5 | -13.7 |
| with trend + discount/premium | 645 | 58.9 | 60.1 | -1.2 | 0.590 | -3.1 | +2.9 |
| NO major BOS (David: invalid) | 3653 | 60.0 | 58.8 | +1.2 | 0.626 | +0.4 | +4.1 |

### Criteria — v5 H1, FX+GOLD pooled, hold = 1 ATR

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 466 | 53.2 | 56.4 | -3.1 | 0.183 | -2.8 | -4.6 |
| major BOS before the return (any delay) | 714 | 55.6 | 56.1 | -0.5 | 0.838 | +0.6 | -4.2 |
| zone inside any major break's move | 719 | 55.6 | 56.1 | -0.5 | 0.831 | +0.6 | -4.2 |
| the break is a CHoCH | 171 | 59.1 | 55.9 | +3.2 | 0.447 | +3.8 | -0.3 |
| BOS gate (3-bar fractal swing) | 1957 | 56.3 | 55.7 | +0.6 | 0.726 | +0.6 | +0.5 |
| displacement >= 2 x avg body | 3056 | 56.7 | 54.1 | +2.6 | 0.149 | +4.9 | -2.9 |
| displacement >= 3 x avg body | 1599 | 56.5 | 55.7 | +0.9 | 0.609 | +3.0 | -4.2 |
| FVG in the leg-out | 3055 | 56.5 | 54.6 | +1.9 | 0.299 | +2.6 | +0.2 |
| FVG >= 0.3 ATR | 2024 | 57.1 | 55.0 | +2.1 | 0.193 | +3.0 | -0.3 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1448 | 57.0 | 55.5 | +1.5 | 0.379 | +2.7 | -1.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3308 | 56.7 | 53.4 | +3.3 | 0.100 | +3.1 | +3.7 |
| base >= 3 candles | 811 | 53.4 | 56.7 | -3.3 | 0.098 | -3.1 | -3.7 |
| departure >= 3 zone heights before the return | 1860 | 53.5 | 58.0 | -4.5 | 0.004 | -3.6 | -6.6 |
| departure >= 2 ATR before the return | 2138 | 55.9 | 56.1 | -0.2 | 0.898 | +0.2 | -1.3 |
| leg-out candle range >= 2 zone heights | 2150 | 53.9 | 58.4 | -4.5 | 0.003 | -2.2 | -10.0 |
| zone height <= 0.5 ATR | 617 | 47.5 | 57.5 | -10.0 | <0.001 | -9.5 | -11.2 |
| zone height > 1 ATR | 1035 | 62.0 | 54.0 | +8.0 | <0.001 | +7.4 | +9.7 |
| with the major trend | 2071 | 54.8 | 57.2 | -2.4 | 0.125 | -4.6 | +2.9 |
| against the major trend | 2039 | 57.3 | 54.7 | +2.6 | 0.107 | +4.9 | -2.9 |
| demand in discount / supply in premium (major range) | 2125 | 56.8 | 55.2 | +1.6 | 0.296 | +2.5 | -0.4 |
| ... of the last 100 bars' range | 2119 | 56.4 | 55.5 | +0.9 | 0.565 | +1.3 | +0.0 |
| liquidity sweep just before the leg-out | 848 | 56.7 | 55.8 | +0.9 | 0.629 | +1.9 | -1.7 |
| round-number level in / at the zone | 1439 | 55.0 | 56.6 | -1.6 | 0.344 | -0.3 | -5.0 |
| RR >= 2 to the nearest live opposing zone | 2458 | 53.8 | 59.2 | -5.4 | <0.001 | -5.7 | -4.6 |
| no live opposing zone above / below | 177 | 56.5 | 56.0 | +0.5 | 0.940 | +0.5 | -1.0 |
| returned within 50 bars | 3496 | 55.8 | 57.3 | -1.5 | 0.483 | -3.6 | +5.1 |
| returned after > 200 bars | 249 | 56.6 | 56.0 | +0.7 | 0.841 | +3.2 | -7.1 |
| formed in Asia (00-07 UTC) | 1400 | 55.5 | 56.3 | -0.8 | 0.634 | -3.7 | +6.4 |
| formed in London (07-12 UTC) | 1005 | 55.2 | 56.3 | -1.0 | 0.577 | +1.1 | -5.7 |
| formed in London/NY overlap (12-16 UTC) | 677 | 64.8 | 54.3 | +10.6 | <0.001 | +8.8 | +15.3 |
| BOS gate + FVG | 421 | 53.2 | 56.3 | -3.1 | 0.239 | -2.8 | -4.5 |
| BOS gate + FVG kept | 279 | 55.2 | 56.1 | -0.9 | 0.792 | -0.9 | -0.9 |
| BOS gate + with trend | 289 | 50.2 | 56.4 | -6.3 | 0.044 | -6.4 | -6.2 |
| BOS gate + discount/premium | 59 | 50.8 | 56.1 | -5.2 | 0.430 | -4.3 | -9.1 |
| BOS gate + sweep | 60 | 56.7 | 56.0 | +0.7 | 1.000 | +3.3 | -17.7 |
| BOS gate + FVG + with trend | 258 | 50.8 | 56.4 | -5.6 | 0.079 | -5.7 | -5.4 |
| BOS gate + FVG + discount/premium | 58 | 51.7 | 56.1 | -4.3 | 0.609 | -3.1 | -9.1 |
| BOS gate + departure >= 3 h | 368 | 51.1 | 56.5 | -5.4 | 0.046 | -5.7 | -4.9 |
| fractal BOS + FVG | 1610 | 56.6 | 55.6 | +0.9 | 0.570 | +0.8 | +1.3 |
| FVG + departure >= 3 h | 1668 | 54.2 | 57.2 | -3.0 | 0.057 | -1.5 | -6.9 |
| sweep + FVG | 651 | 58.4 | 55.6 | +2.8 | 0.199 | +3.9 | -0.1 |
| sweep + major BOS before return | 128 | 56.2 | 56.0 | +0.2 | 1.000 | +1.4 | -5.2 |
| with trend + discount/premium | 645 | 55.0 | 56.2 | -1.2 | 0.599 | -3.1 | +3.0 |
| NO major BOS (David: invalid) | 3653 | 56.4 | 53.2 | +3.1 | 0.196 | +2.8 | +4.6 |

### Criteria — v5 H1, FX+GOLD pooled, hold = 2 zone heights (RR 2)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 466 | 43.1 | 46.7 | -3.6 | 0.153 | -3.3 | -5.1 |
| major BOS before the return (any delay) | 714 | 45.9 | 46.4 | -0.5 | 0.829 | +0.4 | -3.4 |
| zone inside any major break's move | 719 | 45.9 | 46.4 | -0.5 | 0.797 | +0.3 | -3.4 |
| the break is a CHoCH | 171 | 43.9 | 46.4 | -2.6 | 0.533 | -2.5 | -3.5 |
| BOS gate (3-bar fractal swing) | 1957 | 45.8 | 46.8 | -1.0 | 0.511 | -1.1 | -0.8 |
| displacement >= 2 x avg body | 3056 | 46.4 | 46.2 | +0.2 | 0.946 | +2.5 | -5.4 |
| displacement >= 3 x avg body | 1599 | 46.7 | 46.1 | +0.6 | 0.710 | +3.3 | -5.7 |
| FVG in the leg-out | 3055 | 45.6 | 48.5 | -2.9 | 0.099 | -3.3 | -2.1 |
| FVG >= 0.3 ATR | 2024 | 45.5 | 47.2 | -1.7 | 0.280 | -1.3 | -2.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1448 | 45.4 | 46.8 | -1.4 | 0.418 | -0.6 | -3.2 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3308 | 47.2 | 42.8 | +4.4 | 0.023 | +5.7 | +1.2 |
| base >= 3 candles | 811 | 42.8 | 47.2 | -4.4 | 0.024 | -5.7 | -1.2 |
| departure >= 3 zone heights before the return | 1860 | 46.6 | 46.1 | +0.4 | 0.805 | +1.6 | -2.4 |
| departure >= 2 ATR before the return | 2138 | 45.7 | 47.0 | -1.3 | 0.414 | -0.7 | -2.7 |
| leg-out candle range >= 2 zone heights | 2150 | 48.0 | 44.4 | +3.6 | 0.022 | +6.5 | -3.4 |
| zone height <= 0.5 ATR | 617 | 48.6 | 45.9 | +2.7 | 0.229 | +4.0 | -0.5 |
| zone height > 1 ATR | 1035 | 41.0 | 48.1 | -7.2 | <0.001 | -8.8 | -3.2 |
| with the major trend | 2071 | 46.7 | 45.9 | +0.7 | 0.646 | -1.3 | +5.7 |
| against the major trend | 2039 | 46.1 | 46.6 | -0.5 | 0.733 | +1.6 | -5.7 |
| demand in discount / supply in premium (major range) | 2125 | 46.4 | 46.2 | +0.3 | 0.876 | +1.2 | -2.0 |
| ... of the last 100 bars' range | 2119 | 46.1 | 46.6 | -0.4 | 0.778 | +0.0 | -1.4 |
| liquidity sweep just before the leg-out | 848 | 44.2 | 46.9 | -2.6 | 0.171 | -1.7 | -5.2 |
| round-number level in / at the zone | 1439 | 42.9 | 48.2 | -5.3 | 0.001 | -4.2 | -8.1 |
| RR >= 2 to the nearest live opposing zone | 2458 | 47.0 | 45.3 | +1.7 | 0.309 | +2.2 | +0.5 |
| no live opposing zone above / below | 177 | 49.2 | 46.2 | +3.0 | 0.449 | +3.8 | -3.8 |
| returned within 50 bars | 3496 | 46.2 | 46.9 | -0.6 | 0.791 | -2.8 | +6.3 |
| returned after > 200 bars | 249 | 47.0 | 46.3 | +0.7 | 0.842 | +4.4 | -10.4 |
| formed in Asia (00-07 UTC) | 1400 | 47.4 | 45.8 | +1.6 | 0.363 | -1.1 | +8.0 |
| formed in London (07-12 UTC) | 1005 | 45.0 | 46.8 | -1.8 | 0.317 | +0.4 | -6.6 |
| formed in London/NY overlap (12-16 UTC) | 677 | 46.5 | 46.3 | +0.2 | 0.937 | -1.2 | +4.1 |
| BOS gate + FVG | 421 | 42.3 | 46.8 | -4.5 | 0.084 | -4.1 | -6.1 |
| BOS gate + FVG kept | 279 | 44.4 | 46.5 | -2.0 | 0.530 | -2.9 | +0.3 |
| BOS gate + with trend | 289 | 43.3 | 46.6 | -3.3 | 0.301 | -2.6 | -5.5 |
| BOS gate + discount/premium | 59 | 44.1 | 46.4 | -2.3 | 0.784 | +3.3 | -22.6 |
| BOS gate + sweep | 60 | 46.7 | 46.3 | +0.3 | 1.000 | +1.4 | -7.9 |
| BOS gate + FVG + with trend | 258 | 43.0 | 46.5 | -3.5 | 0.281 | -2.7 | -6.0 |
| BOS gate + FVG + discount/premium | 58 | 44.8 | 46.3 | -1.5 | 0.893 | +4.5 | -22.6 |
| BOS gate + departure >= 3 h | 368 | 42.9 | 46.7 | -3.7 | 0.200 | -3.2 | -5.6 |
| fractal BOS + FVG | 1610 | 45.2 | 47.0 | -1.8 | 0.263 | -2.6 | -0.0 |
| FVG + departure >= 3 h | 1668 | 46.4 | 46.3 | +0.1 | 0.955 | +1.4 | -3.0 |
| sweep + FVG | 651 | 44.7 | 46.6 | -1.9 | 0.365 | -1.3 | -3.7 |
| sweep + major BOS before return | 128 | 43.8 | 46.4 | -2.7 | 0.599 | -1.6 | -8.0 |
| with trend + discount/premium | 645 | 46.0 | 46.4 | -0.3 | 0.892 | -2.7 | +4.8 |
| NO major BOS (David: invalid) | 3653 | 46.7 | 43.1 | +3.6 | 0.154 | +3.3 | +5.1 |

### Criteria — v5 GOLD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 397 | 54.7 | 57.4 | -2.8 | 0.303 | -0.9 | -6.7 |
| major BOS before the return (any delay) | 606 | 54.5 | 57.7 | -3.2 | 0.163 | -0.9 | -8.3 |
| zone inside any major break's move | 613 | 54.6 | 57.7 | -3.0 | 0.188 | -0.4 | -8.6 |
| the break is a CHoCH | 138 | 57.2 | 57.1 | +0.2 | 1.000 | -0.7 | +2.4 |
| BOS gate (3-bar fractal swing) | 1546 | 58.0 | 56.3 | +1.7 | 0.349 | +3.3 | -2.4 |
| displacement >= 2 x avg body | 2274 | 56.8 | 57.7 | -0.9 | 0.651 | -3.2 | +4.3 |
| displacement >= 3 x avg body | 1102 | 55.9 | 57.7 | -1.8 | 0.316 | -1.8 | -1.7 |
| FVG in the leg-out | 2497 | 57.5 | 55.5 | +2.0 | 0.354 | +4.2 | -3.0 |
| FVG >= 0.3 ATR | 1654 | 57.7 | 56.4 | +1.3 | 0.459 | +2.4 | -0.8 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1185 | 56.9 | 57.2 | -0.3 | 0.856 | +1.1 | -3.3 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2514 | 57.0 | 57.4 | -0.4 | 0.871 | -0.3 | -1.0 |
| base >= 3 candles | 709 | 57.4 | 57.0 | +0.4 | 0.870 | +0.3 | +1.0 |
| departure >= 3 zone heights before the return | 1427 | 56.3 | 57.7 | -1.3 | 0.476 | +0.8 | -6.2 |
| departure >= 2 ATR before the return | 1682 | 56.9 | 57.3 | -0.4 | 0.840 | +2.6 | -7.4 |
| leg-out candle range >= 2 zone heights | 1508 | 56.7 | 57.4 | -0.7 | 0.700 | -1.6 | +1.2 |
| zone height <= 0.5 ATR | 382 | 57.3 | 57.1 | +0.3 | 0.952 | -1.5 | +4.7 |
| zone height > 1 ATR | 786 | 59.4 | 56.3 | +3.1 | 0.149 | +5.1 | -1.0 |
| with the major trend | 1589 | 58.3 | 55.9 | +2.3 | 0.188 | +1.6 | +3.9 |
| against the major trend | 1630 | 55.9 | 58.3 | -2.4 | 0.172 | -1.8 | -3.9 |
| demand in discount / supply in premium (major range) | 1651 | 57.4 | 56.8 | +0.6 | 0.770 | -0.0 | +1.9 |
| ... of the last 100 bars' range | 1658 | 59.1 | 55.0 | +4.2 | 0.023 | +3.3 | +6.0 |
| liquidity sweep just before the leg-out | 681 | 56.7 | 57.2 | -0.5 | 0.828 | -0.4 | -1.2 |
| round-number level in / at the zone | 1905 | 58.5 | 55.0 | +3.5 | 0.047 | +3.8 | +3.2 |
| RR >= 2 to the nearest live opposing zone | 1952 | 57.9 | 55.9 | +2.0 | 0.256 | +4.5 | -3.7 |
| no live opposing zone above / below | 88 | 62.5 | 56.9 | +5.6 | 0.323 | +4.4 | n/a |
| returned within 50 bars | 2721 | 57.7 | 53.6 | +4.2 | 0.092 | +1.7 | +9.8 |
| returned after > 200 bars | 200 | 55.5 | 57.2 | -1.7 | 0.656 | +1.1 | -9.3 |
| formed in Asia (00-07 UTC) | 979 | 60.2 | 55.7 | +4.4 | 0.021 | +1.8 | +10.7 |
| formed in London (07-12 UTC) | 695 | 57.1 | 57.1 | +0.0 | 1.000 | -0.8 | +1.8 |
| formed in London/NY overlap (12-16 UTC) | 567 | 55.9 | 57.3 | -1.4 | 0.539 | +0.0 | -5.5 |
| BOS gate + FVG | 365 | 55.6 | 57.3 | -1.7 | 0.574 | +0.3 | -5.8 |
| BOS gate + FVG kept | 236 | 55.9 | 57.2 | -1.2 | 0.722 | -1.3 | -0.9 |
| BOS gate + with trend | 259 | 53.3 | 57.4 | -4.1 | 0.207 | -0.9 | -11.6 |
| BOS gate + discount/premium | 46 | 50.0 | 57.2 | -7.2 | 0.379 | -8.4 | -4.3 |
| BOS gate + sweep | 57 | 57.9 | 57.1 | +0.8 | 1.000 | +5.0 | -7.0 |
| BOS gate + FVG + with trend | 242 | 53.3 | 57.4 | -4.1 | 0.227 | -0.6 | -11.9 |
| BOS gate + FVG + discount/premium | 45 | 51.1 | 57.2 | -6.1 | 0.440 | -8.4 | -1.7 |
| BOS gate + departure >= 3 h | 310 | 55.2 | 57.3 | -2.1 | 0.498 | -1.3 | -4.1 |
| fractal BOS + FVG | 1303 | 57.6 | 56.8 | +0.8 | 0.672 | +2.7 | -4.0 |
| FVG + departure >= 3 h | 1319 | 56.6 | 57.4 | -0.8 | 0.668 | +1.1 | -4.8 |
| sweep + FVG | 551 | 56.3 | 57.3 | -1.0 | 0.667 | +0.7 | -5.8 |
| sweep + major BOS before return | 116 | 51.7 | 57.3 | -5.6 | 0.251 | -1.9 | -12.6 |
| with trend + discount/premium | 463 | 61.1 | 56.4 | +4.7 | 0.066 | +2.3 | +10.6 |
| NO major BOS (David: invalid) | 2826 | 57.4 | 54.7 | +2.8 | 0.307 | +0.9 | +6.7 |

### Criteria — v5 GOLD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 49 | 55.1 | 56.6 | -1.5 | 0.876 | -2.6 | -1.0 |
| major BOS before the return (any delay) | 89 | 57.3 | 56.4 | +0.9 | 0.917 | -0.3 | +4.4 |
| zone inside any major break's move | 89 | 57.3 | 56.4 | +0.9 | 0.917 | -0.3 | +4.4 |
| the break is a CHoCH | 16 | 50.0 | 56.6 | -6.6 | 0.622 | -5.1 | -17.9 |
| BOS gate (3-bar fractal swing) | 389 | 60.2 | 53.2 | +7.0 | 0.048 | +8.8 | +4.3 |
| displacement >= 2 x avg body | 596 | 58.2 | 51.9 | +6.3 | 0.129 | +14.7 | -12.6 |
| displacement >= 3 x avg body | 304 | 56.9 | 56.2 | +0.7 | 0.890 | +3.4 | -5.0 |
| FVG in the leg-out | 601 | 57.9 | 52.7 | +5.2 | 0.187 | +3.0 | +12.0 |
| FVG >= 0.3 ATR | 410 | 57.8 | 55.2 | +2.6 | 0.489 | +2.9 | +2.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 296 | 59.1 | 55.0 | +4.1 | 0.265 | +2.5 | +9.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 676 | 57.4 | 52.3 | +5.1 | 0.270 | +4.9 | +5.2 |
| base >= 3 candles | 151 | 52.3 | 57.4 | -5.1 | 0.283 | -4.9 | -5.2 |
| departure >= 3 zone heights before the return | 389 | 57.6 | 55.5 | +2.1 | 0.569 | +1.1 | +5.2 |
| departure >= 2 ATR before the return | 432 | 59.5 | 53.2 | +6.3 | 0.062 | +6.3 | +6.7 |
| leg-out candle range >= 2 zone heights | 445 | 57.5 | 55.2 | +2.3 | 0.515 | +5.9 | -5.5 |
| zone height <= 0.5 ATR | 127 | 55.1 | 56.7 | -1.6 | 0.769 | +2.2 | -8.2 |
| zone height > 1 ATR | 178 | 51.7 | 57.8 | -6.1 | 0.136 | -6.5 | -4.7 |
| with the major trend | 425 | 57.2 | 55.7 | +1.5 | 0.674 | +0.5 | +4.3 |
| against the major trend | 398 | 55.8 | 57.1 | -1.3 | 0.721 | -0.3 | -4.3 |
| demand in discount / supply in premium (major range) | 422 | 56.4 | 56.5 | -0.1 | 1.000 | +2.4 | -7.5 |
| ... of the last 100 bars' range | 421 | 56.3 | 56.7 | -0.4 | 0.947 | -5.0 | +10.7 |
| liquidity sweep just before the leg-out | 145 | 53.8 | 57.0 | -3.2 | 0.518 | -3.1 | -2.5 |
| round-number level in / at the zone | 735 | 55.9 | 60.9 | -5.0 | 0.362 | -1.1 | -19.8 |
| RR >= 2 to the nearest live opposing zone | 496 | 57.9 | 54.4 | +3.5 | 0.349 | +2.5 | +8.7 |
| no live opposing zone above / below | 39 | 71.8 | 55.7 | +16.1 | 0.069 | +13.9 | n/a |
| returned within 50 bars | 703 | 55.6 | 61.3 | -5.7 | 0.276 | -5.0 | -7.7 |
| returned after > 200 bars | 45 | 53.3 | 56.6 | -3.3 | 0.752 | -3.9 | -1.1 |
| formed in Asia (00-07 UTC) | 264 | 54.5 | 57.4 | -2.8 | 0.457 | -7.4 | +7.7 |
| formed in London (07-12 UTC) | 197 | 56.3 | 56.5 | -0.2 | 1.000 | +1.7 | -3.4 |
| formed in London/NY overlap (12-16 UTC) | 133 | 62.4 | 55.3 | +7.1 | 0.153 | +8.5 | +3.4 |
| BOS gate + FVG | 37 | 56.8 | 56.5 | +0.3 | 1.000 | -2.3 | +6.3 |
| BOS gate + FVG kept | 20 | 45.0 | 56.8 | -11.8 | 0.354 | -19.4 | +9.2 |
| BOS gate + with trend | 31 | 58.1 | 56.4 | +1.7 | 1.000 | -0.5 | +6.3 |
| BOS gate + discount/premium | 6 | 66.7 | 56.4 | +10.3 | 0.703 | +7.9 | n/a |
| BOS gate + sweep | 2 | 100.0 | 56.4 | +43.6 | n/a | +41.3 | n/a |
| BOS gate + FVG + with trend | 21 | 61.9 | 56.3 | +5.6 | 0.648 | -0.0 | +24.4 |
| BOS gate + FVG + discount/premium | 5 | 80.0 | 56.3 | +23.7 | 0.391 | +21.3 | n/a |
| BOS gate + departure >= 3 h | 41 | 53.7 | 56.6 | -3.0 | 0.747 | -2.8 | -6.8 |
| fractal BOS + FVG | 310 | 62.9 | 52.6 | +10.3 | 0.004 | +11.0 | +9.9 |
| FVG + departure >= 3 h | 343 | 58.0 | 55.4 | +2.6 | 0.476 | +1.3 | +6.3 |
| sweep + FVG | 107 | 53.3 | 56.9 | -3.7 | 0.532 | -4.1 | -1.2 |
| sweep + major BOS before return | 9 | 55.6 | 56.5 | -0.9 | 1.000 | -1.7 | -1.0 |
| with trend + discount/premium | 112 | 62.5 | 55.5 | +7.0 | 0.172 | +5.9 | +4.9 |
| NO major BOS (David: invalid) | 778 | 56.6 | 55.1 | +1.5 | 0.885 | +2.6 | +1.0 |

### Criteria — v5 EURUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 303 | 56.4 | 58.2 | -1.8 | 0.581 | -2.9 | +2.5 |
| major BOS before the return (any delay) | 497 | 58.6 | 58.0 | +0.6 | 0.807 | -0.4 | +4.1 |
| zone inside any major break's move | 500 | 58.6 | 57.9 | +0.7 | 0.809 | -0.3 | +4.1 |
| the break is a CHoCH | 93 | 61.3 | 57.9 | +3.3 | 0.537 | +5.9 | -3.7 |
| BOS gate (3-bar fractal swing) | 1568 | 58.6 | 57.5 | +1.1 | 0.539 | +0.2 | +3.0 |
| displacement >= 2 x avg body | 2291 | 57.7 | 58.7 | -1.0 | 0.612 | -0.2 | -2.8 |
| displacement >= 3 x avg body | 1068 | 56.1 | 59.0 | -2.9 | 0.124 | -2.6 | -3.6 |
| FVG in the leg-out | 2563 | 57.8 | 59.0 | -1.2 | 0.578 | +1.0 | -6.4 |
| FVG >= 0.3 ATR | 1681 | 58.6 | 57.5 | +1.1 | 0.520 | +2.0 | -1.0 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1188 | 56.9 | 58.7 | -1.8 | 0.334 | -1.0 | -3.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2558 | 57.7 | 59.1 | -1.4 | 0.515 | +0.0 | -4.6 |
| base >= 3 candles | 712 | 59.1 | 57.7 | +1.4 | 0.519 | -0.0 | +4.6 |
| departure >= 3 zone heights before the return | 1407 | 58.0 | 58.1 | -0.1 | 0.968 | -0.1 | +0.1 |
| departure >= 2 ATR before the return | 1705 | 57.8 | 58.3 | -0.4 | 0.803 | +0.1 | -1.7 |
| leg-out candle range >= 2 zone heights | 1455 | 57.2 | 58.7 | -1.6 | 0.374 | -1.5 | -1.8 |
| zone height <= 0.5 ATR | 354 | 55.1 | 58.4 | -3.3 | 0.249 | -5.1 | +0.7 |
| zone height > 1 ATR | 867 | 58.6 | 57.8 | +0.7 | 0.725 | +0.3 | +1.7 |
| with the major trend | 1665 | 58.4 | 57.7 | +0.7 | 0.689 | -1.0 | +4.6 |
| against the major trend | 1602 | 57.7 | 58.3 | -0.6 | 0.742 | +1.1 | -4.6 |
| demand in discount / supply in premium (major range) | 1616 | 57.9 | 58.2 | -0.2 | 0.914 | +0.6 | -2.5 |
| ... of the last 100 bars' range | 1676 | 58.1 | 58.0 | +0.1 | 0.942 | +2.1 | -4.6 |
| liquidity sweep just before the leg-out | 721 | 60.6 | 57.3 | +3.3 | 0.112 | +5.7 | -2.5 |
| round-number level in / at the zone | 284 | 60.6 | 57.8 | +2.8 | 0.381 | +1.9 | +6.0 |
| RR >= 2 to the nearest live opposing zone | 1936 | 57.9 | 58.2 | -0.3 | 0.858 | +0.9 | -3.1 |
| no live opposing zone above / below | 67 | 53.7 | 58.1 | -4.4 | 0.535 | -7.3 | +1.8 |
| returned within 50 bars | 2754 | 58.0 | 58.3 | -0.3 | 0.924 | -0.9 | +0.8 |
| returned after > 200 bars | 199 | 59.3 | 58.0 | +1.3 | 0.769 | -0.8 | +10.1 |
| formed in Asia (00-07 UTC) | 1039 | 57.7 | 58.2 | -0.6 | 0.751 | -1.9 | +2.2 |
| formed in London (07-12 UTC) | 682 | 57.5 | 58.2 | -0.7 | 0.762 | -2.6 | +3.3 |
| formed in London/NY overlap (12-16 UTC) | 550 | 60.2 | 57.6 | +2.6 | 0.268 | +4.0 | -0.8 |
| BOS gate + FVG | 283 | 56.2 | 58.2 | -2.0 | 0.524 | -3.1 | +2.5 |
| BOS gate + FVG kept | 173 | 52.0 | 58.4 | -6.4 | 0.121 | -6.8 | -3.9 |
| BOS gate + with trend | 209 | 54.5 | 58.3 | -3.7 | 0.306 | -6.3 | +5.4 |
| BOS gate + discount/premium | 24 | 58.3 | 58.0 | +0.3 | 1.000 | +4.8 | -26.9 |
| BOS gate + sweep | 39 | 53.8 | 58.1 | -4.2 | 0.618 | -16.6 | +23.5 |
| BOS gate + FVG + with trend | 194 | 54.6 | 58.3 | -3.6 | 0.318 | -5.5 | +4.3 |
| BOS gate + FVG + discount/premium | 24 | 58.3 | 58.0 | +0.3 | 1.000 | +4.8 | -26.9 |
| BOS gate + departure >= 3 h | 224 | 54.9 | 58.3 | -3.4 | 0.318 | -4.7 | +2.5 |
| fractal BOS + FVG | 1324 | 57.9 | 58.2 | -0.3 | 0.881 | -0.0 | -1.1 |
| FVG + departure >= 3 h | 1305 | 58.2 | 58.0 | +0.2 | 0.906 | +0.9 | -1.5 |
| sweep + FVG | 575 | 60.9 | 57.4 | +3.4 | 0.135 | +6.0 | -3.1 |
| sweep + major BOS before return | 84 | 64.3 | 57.9 | +6.4 | 0.268 | +2.3 | +20.3 |
| with trend + discount/premium | 468 | 58.3 | 58.0 | +0.3 | 0.914 | +1.0 | -1.2 |
| NO major BOS (David: invalid) | 2967 | 58.2 | 56.4 | +1.8 | 0.579 | +2.9 | -2.5 |

### Criteria — v5 EURUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 108 | 52.8 | 58.3 | -5.6 | 0.303 | -3.0 | -14.2 |
| major BOS before the return (any delay) | 161 | 55.9 | 58.0 | -2.1 | 0.657 | +1.1 | -14.0 |
| zone inside any major break's move | 161 | 55.9 | 58.0 | -2.1 | 0.657 | +1.1 | -14.0 |
| the break is a CHoCH | 42 | 52.4 | 57.9 | -5.5 | 0.525 | -2.6 | -20.9 |
| BOS gate (3-bar fractal swing) | 402 | 56.2 | 58.9 | -2.7 | 0.437 | -2.8 | -2.2 |
| displacement >= 2 x avg body | 616 | 58.0 | 56.6 | +1.4 | 0.739 | +2.5 | -2.4 |
| displacement >= 3 x avg body | 345 | 57.4 | 57.8 | -0.4 | 0.947 | +3.0 | -9.1 |
| FVG in the leg-out | 640 | 57.0 | 59.6 | -2.5 | 0.561 | +0.0 | -8.3 |
| FVG >= 0.3 ATR | 431 | 56.8 | 58.4 | -1.6 | 0.669 | -0.1 | -5.8 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 319 | 57.4 | 57.8 | -0.4 | 0.942 | +5.1 | -14.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 657 | 59.1 | 52.0 | +7.0 | 0.100 | +8.6 | +4.0 |
| base >= 3 candles | 171 | 52.0 | 59.1 | -7.0 | 0.101 | -8.6 | -4.0 |
| departure >= 3 zone heights before the return | 389 | 60.2 | 55.4 | +4.8 | 0.183 | +7.6 | -2.6 |
| departure >= 2 ATR before the return | 469 | 57.4 | 57.9 | -0.6 | 0.877 | +2.1 | -8.4 |
| leg-out candle range >= 2 zone heights | 420 | 60.0 | 55.1 | +4.9 | 0.159 | +8.4 | -4.3 |
| zone height <= 0.5 ATR | 120 | 60.0 | 57.2 | +2.8 | 0.624 | +3.6 | +1.0 |
| zone height > 1 ATR | 252 | 54.8 | 58.9 | -4.1 | 0.289 | -6.8 | +2.1 |
| with the major trend | 420 | 58.8 | 56.4 | +2.4 | 0.491 | +0.3 | +7.8 |
| against the major trend | 407 | 56.3 | 58.9 | -2.6 | 0.488 | -0.6 | -7.8 |
| demand in discount / supply in premium (major range) | 430 | 56.3 | 59.0 | -2.8 | 0.442 | -5.3 | +2.9 |
| ... of the last 100 bars' range | 424 | 57.5 | 57.7 | -0.1 | 1.000 | -0.3 | -0.3 |
| liquidity sweep just before the leg-out | 189 | 55.6 | 58.2 | -2.7 | 0.553 | -2.3 | -2.8 |
| round-number level in / at the zone | 149 | 57.7 | 57.6 | +0.1 | 1.000 | +0.0 | +1.6 |
| RR >= 2 to the nearest live opposing zone | 483 | 58.4 | 56.5 | +1.9 | 0.608 | +3.2 | -1.0 |
| no live opposing zone above / below | 32 | 62.5 | 57.4 | +5.1 | 0.579 | +3.6 | +11.3 |
| returned within 50 bars | 700 | 58.0 | 55.5 | +2.5 | 0.623 | -3.7 | +25.6 |
| returned after > 200 bars | 49 | 55.1 | 57.8 | -2.7 | 0.766 | +4.8 | -36.7 |
| formed in Asia (00-07 UTC) | 301 | 59.8 | 56.4 | +3.4 | 0.352 | +0.4 | +10.7 |
| formed in London (07-12 UTC) | 210 | 55.7 | 58.3 | -2.5 | 0.569 | -2.0 | -4.7 |
| formed in London/NY overlap (12-16 UTC) | 145 | 56.6 | 57.8 | -1.3 | 0.776 | -1.7 | +1.9 |
| BOS gate + FVG | 103 | 52.4 | 58.3 | -5.9 | 0.287 | -3.4 | -14.2 |
| BOS gate + FVG kept | 65 | 52.3 | 58.1 | -5.8 | 0.434 | -2.8 | -14.7 |
| BOS gate + with trend | 65 | 52.3 | 58.1 | -5.8 | 0.431 | -3.9 | -11.1 |
| BOS gate + discount/premium | 16 | 50.0 | 57.8 | -7.8 | 0.619 | +0.6 | -61.0 |
| BOS gate + sweep | 17 | 64.7 | 57.5 | +7.2 | 0.644 | +6.1 | +39.7 |
| BOS gate + FVG + with trend | 62 | 53.2 | 58.0 | -4.7 | 0.513 | -2.6 | -11.1 |
| BOS gate + FVG + discount/premium | 16 | 50.0 | 57.8 | -7.8 | 0.619 | +0.6 | -61.0 |
| BOS gate + departure >= 3 h | 91 | 50.5 | 58.5 | -7.9 | 0.183 | -6.6 | -11.3 |
| fractal BOS + FVG | 340 | 56.5 | 58.4 | -1.9 | 0.610 | -0.7 | -5.1 |
| FVG + departure >= 3 h | 353 | 60.3 | 55.6 | +4.8 | 0.175 | +7.6 | -2.5 |
| sweep + FVG | 153 | 56.2 | 57.9 | -1.7 | 0.714 | -0.9 | -3.3 |
| sweep + major BOS before return | 35 | 57.1 | 57.6 | -0.5 | 1.000 | +0.2 | -0.4 |
| with trend + discount/premium | 140 | 57.1 | 57.7 | -0.6 | 0.927 | -4.2 | +4.2 |
| NO major BOS (David: invalid) | 720 | 58.3 | 52.8 | +5.6 | 0.292 | +3.0 | +14.2 |

### Criteria — v5 GBPUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 313 | 58.5 | 58.2 | +0.3 | 0.946 | -0.3 | +1.9 |
| major BOS before the return (any delay) | 489 | 56.4 | 58.5 | -2.1 | 0.405 | -3.4 | +1.8 |
| zone inside any major break's move | 501 | 57.1 | 58.4 | -1.3 | 0.579 | -2.2 | +1.2 |
| the break is a CHoCH | 119 | 52.1 | 58.4 | -6.3 | 0.194 | -7.5 | -2.5 |
| BOS gate (3-bar fractal swing) | 1528 | 57.0 | 59.2 | -2.2 | 0.202 | -0.6 | -6.2 |
| displacement >= 2 x avg body | 2295 | 57.8 | 59.0 | -1.2 | 0.512 | -0.2 | -3.8 |
| displacement >= 3 x avg body | 1030 | 58.3 | 58.2 | +0.1 | 0.978 | -0.8 | +2.3 |
| FVG in the leg-out | 2581 | 58.8 | 56.1 | +2.6 | 0.213 | +2.8 | +2.3 |
| FVG >= 0.3 ATR | 1711 | 57.7 | 58.7 | -1.1 | 0.555 | -0.9 | -1.5 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1177 | 60.0 | 57.2 | +2.8 | 0.120 | +2.7 | +2.9 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2619 | 58.4 | 57.5 | +0.9 | 0.698 | -0.4 | +4.0 |
| base >= 3 candles | 694 | 57.5 | 58.4 | -0.9 | 0.691 | +0.4 | -4.0 |
| departure >= 3 zone heights before the return | 1369 | 58.9 | 57.7 | +1.2 | 0.515 | -0.2 | +4.5 |
| departure >= 2 ATR before the return | 1680 | 59.2 | 57.1 | +2.1 | 0.221 | +2.2 | +1.9 |
| leg-out candle range >= 2 zone heights | 1431 | 57.4 | 58.8 | -1.4 | 0.403 | -1.7 | -0.9 |
| zone height <= 0.5 ATR | 355 | 56.3 | 58.4 | -2.1 | 0.465 | -4.3 | +2.7 |
| zone height > 1 ATR | 868 | 59.9 | 57.6 | +2.3 | 0.247 | +3.3 | -0.3 |
| with the major trend | 1667 | 57.4 | 59.0 | -1.6 | 0.356 | -2.0 | -0.6 |
| against the major trend | 1643 | 59.0 | 57.4 | +1.6 | 0.368 | +2.0 | +0.6 |
| demand in discount / supply in premium (major range) | 1663 | 59.4 | 57.0 | +2.3 | 0.177 | +2.0 | +3.2 |
| ... of the last 100 bars' range | 1686 | 58.5 | 57.8 | +0.7 | 0.696 | -0.7 | +4.1 |
| liquidity sweep just before the leg-out | 774 | 60.6 | 57.5 | +3.1 | 0.123 | +2.5 | +4.7 |
| round-number level in / at the zone | 401 | 56.9 | 58.4 | -1.5 | 0.596 | -2.6 | +1.8 |
| RR >= 2 to the nearest live opposing zone | 1898 | 58.2 | 58.2 | +0.1 | 1.000 | +0.2 | -0.4 |
| no live opposing zone above / below | 50 | 64.0 | 58.1 | +5.9 | 0.470 | +5.8 | n/a |
| returned within 50 bars | 2848 | 58.3 | 57.8 | +0.4 | 0.870 | +1.2 | -1.8 |
| returned after > 200 bars | 195 | 54.4 | 58.4 | -4.1 | 0.295 | -5.2 | -0.9 |
| formed in Asia (00-07 UTC) | 1123 | 56.5 | 59.1 | -2.6 | 0.139 | -1.7 | -4.8 |
| formed in London (07-12 UTC) | 708 | 58.8 | 58.0 | +0.7 | 0.766 | +1.2 | -0.5 |
| formed in London/NY overlap (12-16 UTC) | 558 | 60.9 | 57.6 | +3.3 | 0.153 | +3.4 | +3.0 |
| BOS gate + FVG | 287 | 58.9 | 58.1 | +0.8 | 0.834 | -0.6 | +4.5 |
| BOS gate + FVG kept | 191 | 61.8 | 58.0 | +3.8 | 0.324 | +2.4 | +7.2 |
| BOS gate + with trend | 192 | 62.5 | 57.9 | +4.6 | 0.232 | +4.7 | +4.2 |
| BOS gate + discount/premium | 34 | 58.8 | 58.2 | +0.6 | 1.000 | -1.8 | +5.7 |
| BOS gate + sweep | 55 | 65.5 | 58.1 | +7.4 | 0.345 | +10.1 | -3.5 |
| BOS gate + FVG + with trend | 174 | 63.8 | 57.9 | +5.9 | 0.131 | +5.0 | +8.4 |
| BOS gate + FVG + discount/premium | 34 | 58.8 | 58.2 | +0.6 | 1.000 | -1.8 | +5.7 |
| BOS gate + departure >= 3 h | 232 | 59.1 | 58.1 | +0.9 | 0.834 | -0.5 | +5.0 |
| fractal BOS + FVG | 1297 | 57.7 | 58.5 | -0.7 | 0.677 | +1.0 | -5.0 |
| FVG + departure >= 3 h | 1258 | 59.5 | 57.4 | +2.0 | 0.260 | +0.8 | +5.1 |
| sweep + FVG | 616 | 58.8 | 58.1 | +0.7 | 0.752 | +1.0 | -0.1 |
| sweep + major BOS before return | 107 | 57.9 | 58.2 | -0.3 | 1.000 | -0.5 | +0.4 |
| with trend + discount/premium | 467 | 59.1 | 58.0 | +1.1 | 0.676 | -1.4 | +6.0 |
| NO major BOS (David: invalid) | 3000 | 58.2 | 58.5 | -0.3 | 0.950 | +0.3 | -1.9 |

### Criteria — v5 GBPUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 111 | 62.2 | 62.0 | +0.1 | 1.000 | +0.5 | -0.9 |
| major BOS before the return (any delay) | 157 | 63.1 | 61.8 | +1.2 | 0.779 | +2.6 | -2.3 |
| zone inside any major break's move | 159 | 63.5 | 61.7 | +1.8 | 0.723 | +3.3 | -2.3 |
| the break is a CHoCH | 42 | 69.0 | 61.7 | +7.4 | 0.410 | +4.2 | +23.5 |
| BOS gate (3-bar fractal swing) | 390 | 61.8 | 62.3 | -0.5 | 0.879 | -3.3 | +6.5 |
| displacement >= 2 x avg body | 634 | 61.4 | 64.4 | -3.0 | 0.490 | +2.2 | -14.7 |
| displacement >= 3 x avg body | 319 | 64.6 | 60.5 | +4.1 | 0.239 | +7.1 | -3.5 |
| FVG in the leg-out | 605 | 61.2 | 64.5 | -3.4 | 0.418 | -2.9 | -4.2 |
| FVG >= 0.3 ATR | 395 | 61.8 | 62.3 | -0.6 | 0.888 | +1.0 | -4.3 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 290 | 60.0 | 63.2 | -3.2 | 0.405 | -3.4 | -2.6 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 677 | 61.7 | 63.5 | -1.8 | 0.711 | -3.2 | +2.1 |
| base >= 3 candles | 148 | 63.5 | 61.7 | +1.8 | 0.723 | +3.2 | -2.1 |
| departure >= 3 zone heights before the return | 342 | 62.6 | 61.7 | +0.9 | 0.834 | +4.3 | -7.8 |
| departure >= 2 ATR before the return | 416 | 62.0 | 62.1 | -0.1 | 1.000 | +0.3 | -0.7 |
| leg-out candle range >= 2 zone heights | 411 | 63.5 | 60.6 | +2.9 | 0.428 | +7.4 | -8.3 |
| zone height <= 0.5 ATR | 121 | 62.8 | 61.9 | +0.9 | 0.917 | +4.6 | -10.5 |
| zone height > 1 ATR | 257 | 58.4 | 63.7 | -5.4 | 0.158 | -7.1 | -1.0 |
| with the major trend | 406 | 61.8 | 62.3 | -0.5 | 0.937 | -0.5 | -0.3 |
| against the major trend | 418 | 62.4 | 61.7 | +0.8 | 0.824 | +1.0 | +0.3 |
| demand in discount / supply in premium (major range) | 412 | 61.4 | 62.7 | -1.3 | 0.721 | -0.7 | -2.9 |
| ... of the last 100 bars' range | 424 | 61.3 | 62.8 | -1.5 | 0.681 | -1.4 | -2.1 |
| liquidity sweep just before the leg-out | 185 | 61.1 | 62.3 | -1.3 | 0.800 | +3.3 | -12.2 |
| round-number level in / at the zone | 212 | 58.5 | 63.3 | -4.8 | 0.218 | -7.5 | +3.9 |
| RR >= 2 to the nearest live opposing zone | 495 | 61.2 | 63.3 | -2.1 | 0.561 | +1.0 | -9.9 |
| no live opposing zone above / below | 22 | 50.0 | 62.4 | -12.4 | 0.276 | -12.2 | n/a |
| returned within 50 bars | 686 | 61.4 | 65.5 | -4.1 | 0.405 | -6.0 | +1.3 |
| returned after > 200 bars | 66 | 66.7 | 61.7 | +5.0 | 0.432 | +9.0 | -7.1 |
| formed in Asia (00-07 UTC) | 327 | 62.7 | 61.6 | +1.0 | 0.775 | +3.0 | -3.7 |
| formed in London (07-12 UTC) | 211 | 61.6 | 62.2 | -0.6 | 0.936 | +0.4 | -3.0 |
| formed in London/NY overlap (12-16 UTC) | 145 | 65.5 | 61.3 | +4.2 | 0.358 | +1.2 | +11.3 |
| BOS gate + FVG | 100 | 62.0 | 62.1 | -0.1 | 1.000 | +0.9 | -2.4 |
| BOS gate + FVG kept | 76 | 67.1 | 61.5 | +5.6 | 0.388 | +3.5 | +11.8 |
| BOS gate + with trend | 68 | 58.8 | 62.4 | -3.5 | 0.607 | -0.9 | -9.2 |
| BOS gate + discount/premium | 15 | 46.7 | 62.3 | -15.7 | 0.284 | -15.9 | -13.0 |
| BOS gate + sweep | 18 | 61.1 | 62.1 | -1.0 | 1.000 | -1.8 | +3.8 |
| BOS gate + FVG + with trend | 60 | 58.3 | 62.4 | -4.0 | 0.586 | -1.3 | -9.2 |
| BOS gate + FVG + discount/premium | 15 | 46.7 | 62.3 | -15.7 | 0.284 | -15.9 | -13.0 |
| BOS gate + departure >= 3 h | 80 | 61.3 | 62.1 | -0.9 | 0.894 | -0.5 | -1.9 |
| fractal BOS + FVG | 327 | 60.9 | 62.9 | -2.0 | 0.605 | -3.9 | +2.7 |
| FVG + departure >= 3 h | 313 | 61.7 | 62.3 | -0.6 | 0.883 | +3.5 | -11.5 |
| sweep + FVG | 137 | 59.1 | 62.6 | -3.5 | 0.443 | -1.6 | -8.2 |
| sweep + major BOS before return | 30 | 50.0 | 62.5 | -12.5 | 0.187 | -4.8 | -30.7 |
| with trend + discount/premium | 102 | 60.8 | 62.2 | -1.5 | 0.834 | -2.6 | +1.6 |
| NO major BOS (David: invalid) | 714 | 62.0 | 62.2 | -0.1 | 1.000 | -0.5 | +0.9 |

### Criteria — v5 USDJPY M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 301 | 60.5 | 58.3 | +2.1 | 0.500 | +2.4 | +2.0 |
| major BOS before the return (any delay) | 467 | 59.7 | 58.3 | +1.4 | 0.569 | +0.4 | +6.8 |
| zone inside any major break's move | 475 | 59.6 | 58.3 | +1.2 | 0.616 | +0.3 | +6.4 |
| the break is a CHoCH | 106 | 63.2 | 58.4 | +4.8 | 0.358 | +4.7 | +7.7 |
| BOS gate (3-bar fractal swing) | 1534 | 57.7 | 59.3 | -1.6 | 0.373 | -3.3 | +2.3 |
| displacement >= 2 x avg body | 2323 | 58.2 | 59.3 | -1.1 | 0.537 | -2.4 | +1.8 |
| displacement >= 3 x avg body | 1095 | 58.6 | 58.5 | +0.2 | 0.940 | -0.5 | +1.6 |
| FVG in the leg-out | 2537 | 58.3 | 59.4 | -1.2 | 0.589 | +1.7 | -7.2 |
| FVG >= 0.3 ATR | 1745 | 58.2 | 58.9 | -0.6 | 0.707 | +0.3 | -2.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1127 | 57.9 | 58.9 | -1.0 | 0.574 | +1.2 | -6.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2575 | 58.6 | 58.4 | +0.2 | 0.968 | +0.7 | -0.9 |
| base >= 3 candles | 709 | 58.4 | 58.6 | -0.2 | 0.964 | -0.7 | +0.9 |
| departure >= 3 zone heights before the return | 1487 | 58.0 | 58.9 | -0.9 | 0.619 | -0.8 | -1.2 |
| departure >= 2 ATR before the return | 1742 | 59.2 | 57.8 | +1.4 | 0.428 | +2.5 | -1.2 |
| leg-out candle range >= 2 zone heights | 1571 | 56.8 | 60.1 | -3.3 | 0.054 | -4.5 | -0.9 |
| zone height <= 0.5 ATR | 447 | 53.9 | 59.3 | -5.3 | 0.033 | -5.4 | -5.4 |
| zone height > 1 ATR | 780 | 59.0 | 58.4 | +0.6 | 0.798 | +0.2 | +1.6 |
| with the major trend | 1666 | 58.9 | 58.1 | +0.8 | 0.640 | +1.5 | -0.8 |
| against the major trend | 1614 | 58.2 | 58.9 | -0.7 | 0.692 | -1.3 | +0.8 |
| demand in discount / supply in premium (major range) | 1620 | 58.7 | 58.4 | +0.4 | 0.863 | +1.1 | -1.4 |
| ... of the last 100 bars' range | 1640 | 59.1 | 57.9 | +1.2 | 0.493 | +1.8 | -0.2 |
| liquidity sweep just before the leg-out | 690 | 60.6 | 58.0 | +2.6 | 0.227 | +2.1 | +3.8 |
| round-number level in / at the zone | 454 | 61.9 | 58.0 | +3.9 | 0.118 | +3.4 | +5.5 |
| RR >= 2 to the nearest live opposing zone | 1997 | 58.0 | 59.4 | -1.4 | 0.447 | -1.7 | -0.6 |
| no live opposing zone above / below | 106 | 58.5 | 58.5 | -0.0 | 1.000 | -1.4 | +2.0 |
| returned within 50 bars | 2804 | 58.8 | 56.7 | +2.2 | 0.392 | +1.2 | +4.4 |
| returned after > 200 bars | 209 | 53.1 | 58.9 | -5.8 | 0.105 | -3.7 | -11.5 |
| formed in Asia (00-07 UTC) | 967 | 59.0 | 58.3 | +0.7 | 0.701 | -0.8 | +4.4 |
| formed in London (07-12 UTC) | 622 | 61.9 | 57.7 | +4.2 | 0.059 | +6.5 | -0.8 |
| formed in London/NY overlap (12-16 UTC) | 555 | 57.7 | 58.7 | -1.0 | 0.670 | -1.4 | -0.1 |
| BOS gate + FVG | 270 | 60.4 | 58.4 | +2.0 | 0.550 | +1.9 | +3.9 |
| BOS gate + FVG kept | 180 | 58.9 | 58.5 | +0.4 | 0.941 | +0.6 | +0.2 |
| BOS gate + with trend | 194 | 59.3 | 58.5 | +0.8 | 0.879 | +1.2 | -0.4 |
| BOS gate + discount/premium | 40 | 65.0 | 58.4 | +6.6 | 0.438 | +3.9 | +41.1 |
| BOS gate + sweep | 38 | 68.4 | 58.4 | +10.0 | 0.247 | +6.5 | +41.1 |
| BOS gate + FVG + with trend | 173 | 58.4 | 58.5 | -0.2 | 1.000 | +0.5 | -3.1 |
| BOS gate + FVG + discount/premium | 38 | 63.2 | 58.5 | +4.7 | 0.619 | +2.9 | +41.0 |
| BOS gate + departure >= 3 h | 233 | 60.1 | 58.4 | +1.7 | 0.621 | +2.2 | -0.4 |
| fractal BOS + FVG | 1276 | 57.5 | 59.2 | -1.6 | 0.362 | -2.0 | -0.9 |
| FVG + departure >= 3 h | 1337 | 57.2 | 59.4 | -2.2 | 0.221 | -1.7 | -3.3 |
| sweep + FVG | 543 | 60.8 | 58.1 | +2.7 | 0.245 | +2.7 | +2.7 |
| sweep + major BOS before return | 84 | 60.7 | 58.5 | +2.2 | 0.739 | -1.4 | +24.6 |
| with trend + discount/premium | 558 | 59.0 | 58.4 | +0.5 | 0.863 | +2.0 | -2.0 |
| NO major BOS (David: invalid) | 2983 | 58.3 | 60.5 | -2.1 | 0.499 | -2.4 | -2.0 |

### Criteria — v5 USDJPY H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 88 | 63.6 | 62.2 | +1.4 | 0.805 | +2.9 | -5.7 |
| major BOS before the return (any delay) | 135 | 62.2 | 62.4 | -0.2 | 1.000 | +0.4 | -2.7 |
| zone inside any major break's move | 137 | 62.0 | 62.4 | -0.4 | 1.000 | +0.1 | -2.7 |
| the break is a CHoCH | 31 | 67.7 | 62.2 | +5.6 | 0.574 | +4.6 | +12.7 |
| BOS gate (3-bar fractal swing) | 395 | 63.8 | 61.1 | +2.7 | 0.433 | +3.6 | +0.6 |
| displacement >= 2 x avg body | 593 | 61.6 | 64.4 | -2.9 | 0.467 | -4.5 | +1.0 |
| displacement >= 3 x avg body | 308 | 61.0 | 63.1 | -2.1 | 0.560 | -2.6 | -0.9 |
| FVG in the leg-out | 600 | 63.5 | 59.4 | +4.1 | 0.295 | +3.1 | +6.3 |
| FVG >= 0.3 ATR | 387 | 65.4 | 59.7 | +5.6 | 0.101 | +3.3 | +11.3 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 267 | 62.9 | 62.1 | +0.8 | 0.876 | +1.1 | +0.3 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 655 | 63.7 | 57.5 | +6.2 | 0.132 | +8.2 | +1.0 |
| base >= 3 candles | 174 | 57.5 | 63.7 | -6.2 | 0.145 | -8.2 | -1.0 |
| departure >= 3 zone heights before the return | 379 | 61.2 | 63.3 | -2.1 | 0.566 | -1.8 | -2.9 |
| departure >= 2 ATR before the return | 411 | 60.6 | 64.1 | -3.5 | 0.320 | -4.1 | -2.2 |
| leg-out candle range >= 2 zone heights | 460 | 61.5 | 63.4 | -1.9 | 0.612 | -1.0 | -4.2 |
| zone height <= 0.5 ATR | 138 | 56.5 | 63.5 | -7.0 | 0.131 | -8.9 | -3.1 |
| zone height > 1 ATR | 163 | 63.2 | 62.2 | +1.0 | 0.852 | -2.3 | +11.0 |
| with the major trend | 423 | 59.6 | 65.3 | -5.7 | 0.099 | -8.1 | -0.2 |
| against the major trend | 405 | 65.4 | 59.4 | +6.0 | 0.089 | +8.5 | +0.2 |
| demand in discount / supply in premium (major range) | 428 | 62.4 | 62.3 | +0.0 | 1.000 | +1.5 | -3.4 |
| ... of the last 100 bars' range | 422 | 62.8 | 61.9 | +0.9 | 0.817 | +4.0 | -6.5 |
| liquidity sweep just before the leg-out | 163 | 61.3 | 62.6 | -1.3 | 0.782 | -4.4 | +6.9 |
| round-number level in / at the zone | 213 | 64.3 | 61.7 | +2.6 | 0.510 | +1.3 | +6.9 |
| RR >= 2 to the nearest live opposing zone | 509 | 62.9 | 61.6 | +1.3 | 0.716 | +2.0 | -0.4 |
| no live opposing zone above / below | 50 | 50.0 | 63.2 | -13.2 | 0.070 | -14.7 | -10.3 |
| returned within 50 bars | 712 | 62.1 | 64.1 | -2.0 | 0.662 | -3.9 | +4.6 |
| returned after > 200 bars | 35 | 60.0 | 62.5 | -2.5 | 0.848 | -3.9 | +4.3 |
| formed in Asia (00-07 UTC) | 261 | 64.8 | 61.3 | +3.5 | 0.363 | -2.5 | +17.2 |
| formed in London (07-12 UTC) | 185 | 60.0 | 63.0 | -3.0 | 0.489 | -0.3 | -9.0 |
| formed in London/NY overlap (12-16 UTC) | 113 | 66.4 | 61.7 | +4.6 | 0.350 | +4.1 | +6.0 |
| BOS gate + FVG | 81 | 63.0 | 62.3 | +0.7 | 1.000 | +1.7 | -4.4 |
| BOS gate + FVG kept | 55 | 67.3 | 62.0 | +5.3 | 0.464 | +4.8 | +9.2 |
| BOS gate + with trend | 56 | 62.5 | 62.4 | +0.1 | 1.000 | +3.2 | -13.0 |
| BOS gate + discount/premium | 8 | 75.0 | 62.2 | +12.8 | 0.518 | +9.2 | +37.7 |
| BOS gate + sweep | 10 | 70.0 | 62.3 | +7.7 | 0.745 | +7.8 | n/a |
| BOS gate + FVG + with trend | 52 | 61.5 | 62.4 | -0.9 | 1.000 | +1.4 | -12.9 |
| BOS gate + FVG + discount/premium | 8 | 75.0 | 62.2 | +12.8 | 0.518 | +9.2 | +37.7 |
| BOS gate + departure >= 3 h | 66 | 60.6 | 62.5 | -1.9 | 0.791 | -1.3 | -4.4 |
| fractal BOS + FVG | 317 | 64.7 | 60.9 | +3.7 | 0.306 | +3.1 | +5.3 |
| FVG + departure >= 3 h | 335 | 61.8 | 62.8 | -1.0 | 0.827 | -0.7 | -1.5 |
| sweep + FVG | 129 | 62.0 | 62.4 | -0.4 | 1.000 | -3.3 | +8.5 |
| sweep + major BOS before return | 22 | 63.6 | 62.3 | +1.3 | 1.000 | -0.4 | +37.7 |
| with trend + discount/premium | 168 | 57.1 | 63.7 | -6.5 | 0.125 | -12.4 | +0.7 |
| NO major BOS (David: invalid) | 741 | 62.2 | 63.6 | -1.4 | 0.809 | -2.9 | +5.7 |

### Criteria — v5 AUDUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 297 | 59.3 | 56.4 | +2.8 | 0.349 | +3.2 | +1.9 |
| major BOS before the return (any delay) | 493 | 57.8 | 56.5 | +1.3 | 0.626 | +2.0 | -0.6 |
| zone inside any major break's move | 501 | 57.9 | 56.5 | +1.4 | 0.584 | +2.1 | -0.6 |
| the break is a CHoCH | 105 | 62.9 | 56.5 | +6.4 | 0.223 | +6.2 | +6.9 |
| BOS gate (3-bar fractal swing) | 1521 | 54.7 | 58.5 | -3.8 | 0.026 | -2.8 | -6.4 |
| displacement >= 2 x avg body | 2234 | 57.1 | 55.9 | +1.2 | 0.540 | +1.8 | -0.2 |
| displacement >= 3 x avg body | 1082 | 55.8 | 57.2 | -1.3 | 0.480 | +0.4 | -5.7 |
| FVG in the leg-out | 2461 | 57.7 | 53.4 | +4.3 | 0.040 | +4.1 | +5.0 |
| FVG >= 0.3 ATR | 1640 | 58.0 | 55.4 | +2.6 | 0.141 | +2.7 | +2.5 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1113 | 58.0 | 56.0 | +1.9 | 0.304 | +1.0 | +4.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2511 | 57.7 | 53.0 | +4.7 | 0.032 | +3.9 | +6.6 |
| base >= 3 candles | 679 | 53.0 | 57.7 | -4.7 | 0.033 | -3.9 | -6.6 |
| departure >= 3 zone heights before the return | 1431 | 57.0 | 56.5 | +0.4 | 0.806 | -1.9 | +6.1 |
| departure >= 2 ATR before the return | 1675 | 58.0 | 55.2 | +2.8 | 0.119 | +1.3 | +6.5 |
| leg-out candle range >= 2 zone heights | 1438 | 56.3 | 57.0 | -0.7 | 0.718 | -1.6 | +1.6 |
| zone height <= 0.5 ATR | 344 | 48.8 | 57.7 | -8.8 | 0.002 | -10.7 | -5.4 |
| zone height > 1 ATR | 808 | 57.9 | 56.3 | +1.6 | 0.421 | +4.1 | -4.8 |
| with the major trend | 1578 | 55.3 | 58.1 | -2.7 | 0.108 | -1.6 | -5.5 |
| against the major trend | 1612 | 58.1 | 55.3 | +2.7 | 0.126 | +1.6 | +5.5 |
| demand in discount / supply in premium (major range) | 1667 | 58.2 | 55.1 | +3.1 | 0.085 | +2.4 | +4.7 |
| ... of the last 100 bars' range | 1659 | 58.2 | 55.1 | +3.0 | 0.094 | +1.7 | +6.3 |
| liquidity sweep just before the leg-out | 750 | 59.3 | 55.9 | +3.4 | 0.104 | +2.7 | +5.4 |
| round-number level in / at the zone | 250 | 59.2 | 56.5 | +2.7 | 0.413 | -0.8 | +14.4 |
| RR >= 2 to the nearest live opposing zone | 1900 | 58.1 | 54.7 | +3.3 | 0.061 | +3.0 | +4.2 |
| no live opposing zone above / below | 76 | 43.4 | 57.0 | -13.6 | 0.021 | -13.8 | n/a |
| returned within 50 bars | 2740 | 56.8 | 56.4 | +0.3 | 0.918 | -0.6 | +2.8 |
| returned after > 200 bars | 184 | 57.6 | 56.7 | +1.0 | 0.819 | -1.2 | +8.0 |
| formed in Asia (00-07 UTC) | 993 | 56.8 | 56.7 | +0.1 | 0.970 | -0.6 | +1.8 |
| formed in London (07-12 UTC) | 655 | 60.3 | 55.8 | +4.5 | 0.034 | +4.0 | +5.8 |
| formed in London/NY overlap (12-16 UTC) | 551 | 56.4 | 56.8 | -0.3 | 0.921 | -0.1 | -1.0 |
| BOS gate + FVG | 260 | 58.1 | 56.6 | +1.5 | 0.652 | +1.7 | +1.1 |
| BOS gate + FVG kept | 180 | 59.4 | 56.5 | +2.9 | 0.480 | +1.5 | +6.4 |
| BOS gate + with trend | 192 | 57.3 | 56.7 | +0.6 | 0.881 | +1.2 | -0.8 |
| BOS gate + discount/premium | 35 | 57.1 | 56.7 | +0.4 | 1.000 | -6.8 | +21.3 |
| BOS gate + sweep | 49 | 59.2 | 56.7 | +2.5 | 0.775 | -0.3 | +13.5 |
| BOS gate + FVG + with trend | 166 | 54.2 | 56.8 | -2.6 | 0.506 | -2.5 | -3.0 |
| BOS gate + FVG + discount/premium | 34 | 55.9 | 56.7 | -0.8 | 1.000 | -8.8 | +21.3 |
| BOS gate + departure >= 3 h | 228 | 60.1 | 56.4 | +3.6 | 0.307 | +3.4 | +4.2 |
| fractal BOS + FVG | 1263 | 55.8 | 57.3 | -1.5 | 0.420 | -0.4 | -4.0 |
| FVG + departure >= 3 h | 1312 | 57.2 | 56.4 | +0.8 | 0.694 | -1.3 | +5.8 |
| sweep + FVG | 614 | 59.4 | 56.1 | +3.4 | 0.139 | +3.3 | +3.7 |
| sweep + major BOS before return | 105 | 56.2 | 56.7 | -0.5 | 0.921 | +0.1 | -2.6 |
| with trend + discount/premium | 510 | 56.3 | 56.8 | -0.5 | 0.843 | -0.9 | +0.4 |
| NO major BOS (David: invalid) | 2893 | 56.4 | 59.3 | -2.8 | 0.358 | -3.2 | -1.9 |

### Criteria — v5 AUDUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 110 | 59.1 | 61.3 | -2.2 | 0.664 | -0.7 | -5.1 |
| major BOS before the return (any delay) | 172 | 59.3 | 61.4 | -2.1 | 0.666 | +0.8 | -9.8 |
| zone inside any major break's move | 173 | 59.0 | 61.5 | -2.6 | 0.545 | +0.2 | -9.8 |
| the break is a CHoCH | 40 | 62.5 | 60.9 | +1.6 | 0.875 | +10.5 | -19.2 |
| BOS gate (3-bar fractal swing) | 381 | 59.1 | 62.7 | -3.6 | 0.327 | -4.8 | -0.9 |
| displacement >= 2 x avg body | 617 | 62.4 | 56.5 | +5.9 | 0.155 | +5.2 | +7.6 |
| displacement >= 3 x avg body | 323 | 60.4 | 61.4 | -1.0 | 0.823 | -1.3 | -0.2 |
| FVG in the leg-out | 609 | 60.1 | 63.7 | -3.6 | 0.406 | -3.9 | -2.9 |
| FVG >= 0.3 ATR | 401 | 58.9 | 63.1 | -4.2 | 0.229 | -5.8 | -0.5 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 276 | 60.1 | 61.4 | -1.3 | 0.748 | -0.6 | -2.9 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 643 | 62.7 | 54.5 | +8.2 | 0.065 | +5.4 | +15.0 |
| base >= 3 candles | 167 | 54.5 | 62.7 | -8.2 | 0.062 | -5.4 | -15.0 |
| departure >= 3 zone heights before the return | 361 | 56.2 | 64.8 | -8.6 | 0.015 | -9.9 | -5.3 |
| departure >= 2 ATR before the return | 410 | 57.8 | 64.2 | -6.4 | 0.061 | -8.4 | -1.9 |
| leg-out candle range >= 2 zone heights | 414 | 60.4 | 61.6 | -1.2 | 0.781 | -2.8 | +2.5 |
| zone height <= 0.5 ATR | 111 | 57.7 | 61.5 | -3.9 | 0.463 | -5.8 | +0.8 |
| zone height > 1 ATR | 185 | 58.4 | 61.8 | -3.4 | 0.445 | -3.6 | -2.8 |
| with the major trend | 397 | 61.5 | 60.5 | +0.9 | 0.829 | -3.3 | +11.3 |
| against the major trend | 411 | 60.8 | 61.2 | -0.3 | 0.945 | +4.2 | -11.3 |
| demand in discount / supply in premium (major range) | 433 | 61.7 | 60.2 | +1.5 | 0.718 | +2.9 | -1.9 |
| ... of the last 100 bars' range | 428 | 62.6 | 59.2 | +3.5 | 0.348 | +5.9 | -2.5 |
| liquidity sweep just before the leg-out | 166 | 57.2 | 62.0 | -4.7 | 0.295 | +0.5 | -17.7 |
| round-number level in / at the zone | 130 | 53.1 | 62.5 | -9.4 | 0.045 | -13.3 | +2.5 |
| RR >= 2 to the nearest live opposing zone | 475 | 59.8 | 62.7 | -2.9 | 0.407 | -3.8 | -0.1 |
| no live opposing zone above / below | 34 | 55.9 | 61.2 | -5.3 | 0.596 | -5.9 | n/a |
| returned within 50 bars | 695 | 61.2 | 60.0 | +1.2 | 0.833 | -1.8 | +11.1 |
| returned after > 200 bars | 54 | 61.1 | 61.0 | +0.1 | 1.000 | +4.7 | -10.6 |
| formed in Asia (00-07 UTC) | 247 | 64.4 | 59.5 | +4.9 | 0.205 | +8.6 | -4.3 |
| formed in London (07-12 UTC) | 202 | 59.4 | 61.5 | -2.1 | 0.616 | -1.9 | -2.5 |
| formed in London/NY overlap (12-16 UTC) | 141 | 62.4 | 60.7 | +1.7 | 0.709 | -4.3 | +19.3 |
| BOS gate + FVG | 100 | 59.0 | 61.3 | -2.3 | 0.750 | -1.3 | -4.2 |
| BOS gate + FVG kept | 63 | 60.3 | 61.0 | -0.7 | 1.000 | +2.9 | -6.4 |
| BOS gate + with trend | 69 | 58.0 | 61.3 | -3.3 | 0.602 | -6.4 | +2.9 |
| BOS gate + discount/premium | 14 | 57.1 | 61.1 | -3.9 | 0.794 | +5.3 | -10.3 |
| BOS gate + sweep | 13 | 53.8 | 61.1 | -7.3 | 0.780 | +5.3 | -35.5 |
| BOS gate + FVG + with trend | 63 | 58.7 | 61.2 | -2.4 | 0.796 | -6.1 | +5.6 |
| BOS gate + FVG + discount/premium | 14 | 57.1 | 61.1 | -3.9 | 0.794 | +5.3 | -10.3 |
| BOS gate + departure >= 3 h | 90 | 58.9 | 61.3 | -2.4 | 0.728 | -3.5 | +0.1 |
| fractal BOS + FVG | 316 | 57.6 | 63.2 | -5.6 | 0.121 | -6.6 | -3.1 |
| FVG + departure >= 3 h | 324 | 56.5 | 64.0 | -7.5 | 0.036 | -9.1 | -3.8 |
| sweep + FVG | 125 | 59.2 | 61.3 | -2.1 | 0.686 | +3.1 | -15.0 |
| sweep + major BOS before return | 32 | 53.1 | 61.3 | -8.2 | 0.351 | -5.7 | -17.6 |
| with trend + discount/premium | 123 | 58.5 | 61.4 | -2.9 | 0.555 | -2.5 | -3.7 |
| NO major BOS (David: invalid) | 700 | 61.3 | 59.1 | +2.2 | 0.685 | +0.7 | +5.1 |

### Criteria — v5 BITCOIN M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 254 | 59.4 | 57.9 | +1.5 | 0.652 | +3.3 | -1.9 |
| major BOS before the return (any delay) | 449 | 61.0 | 57.6 | +3.5 | 0.188 | +5.7 | -1.4 |
| zone inside any major break's move | 453 | 60.9 | 57.6 | +3.4 | 0.189 | +5.4 | -1.0 |
| the break is a CHoCH | 89 | 56.2 | 58.1 | -1.9 | 0.743 | +0.0 | -5.0 |
| BOS gate (3-bar fractal swing) | 1695 | 56.9 | 59.2 | -2.2 | 0.202 | -2.6 | -1.4 |
| displacement >= 2 x avg body | 2399 | 58.1 | 57.9 | +0.1 | 0.971 | +0.1 | +0.2 |
| displacement >= 3 x avg body | 1163 | 57.6 | 58.3 | -0.7 | 0.752 | -0.3 | -1.4 |
| FVG in the leg-out | 2674 | 58.6 | 55.5 | +3.1 | 0.159 | +5.2 | -2.3 |
| FVG >= 0.3 ATR | 1782 | 58.4 | 57.7 | +0.7 | 0.685 | -0.2 | +2.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1232 | 61.6 | 55.9 | +5.7 | 0.001 | +6.5 | +3.8 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2672 | 57.8 | 58.9 | -1.1 | 0.615 | -2.9 | +3.4 |
| base >= 3 candles | 652 | 58.9 | 57.8 | +1.1 | 0.638 | +2.9 | -3.4 |
| departure >= 3 zone heights before the return | 1561 | 60.3 | 56.0 | +4.2 | 0.015 | +5.3 | +1.7 |
| departure >= 2 ATR before the return | 1810 | 60.3 | 55.3 | +5.0 | 0.004 | +6.8 | +1.0 |
| leg-out candle range >= 2 zone heights | 1675 | 56.4 | 59.7 | -3.3 | 0.058 | -4.5 | -0.3 |
| zone height <= 0.5 ATR | 405 | 55.1 | 58.4 | -3.4 | 0.205 | -5.0 | +0.1 |
| zone height > 1 ATR | 766 | 58.5 | 57.9 | +0.6 | 0.797 | +0.4 | +1.1 |
| with the major trend | 1667 | 58.5 | 57.5 | +1.0 | 0.558 | +3.2 | -4.1 |
| against the major trend | 1656 | 57.5 | 58.6 | -1.1 | 0.530 | -3.3 | +4.1 |
| demand in discount / supply in premium (major range) | 1672 | 57.7 | 58.4 | -0.6 | 0.718 | -1.3 | +0.9 |
| ... of the last 100 bars' range | 1668 | 57.2 | 58.9 | -1.7 | 0.356 | -1.4 | -2.4 |
| liquidity sweep just before the leg-out | 661 | 60.4 | 57.5 | +2.9 | 0.185 | +2.0 | +4.9 |
| round-number level in / at the zone | 555 | 59.8 | 57.7 | +2.1 | 0.360 | +2.9 | -0.2 |
| RR >= 2 to the nearest live opposing zone | 2036 | 58.3 | 57.6 | +0.7 | 0.716 | +0.6 | +0.9 |
| no live opposing zone above / below | 38 | 52.6 | 58.1 | -5.5 | 0.514 | -5.6 | n/a |
| returned within 50 bars | 2810 | 57.8 | 59.1 | -1.3 | 0.591 | -3.2 | +3.4 |
| returned after > 200 bars | 230 | 61.3 | 57.8 | +3.5 | 0.304 | +5.9 | -2.5 |
| formed in Asia (00-07 UTC) | 973 | 56.7 | 58.6 | -1.8 | 0.330 | -3.0 | +1.1 |
| formed in London (07-12 UTC) | 724 | 54.8 | 58.9 | -4.1 | 0.048 | -1.1 | -11.1 |
| formed in London/NY overlap (12-16 UTC) | 617 | 62.1 | 57.1 | +5.0 | 0.026 | +3.3 | +9.0 |
| BOS gate + FVG | 223 | 60.1 | 57.9 | +2.2 | 0.530 | +4.0 | -1.2 |
| BOS gate + FVG kept | 147 | 63.3 | 57.8 | +5.5 | 0.204 | +8.5 | +1.0 |
| BOS gate + with trend | 165 | 61.2 | 57.9 | +3.3 | 0.416 | +4.7 | +0.3 |
| BOS gate + discount/premium | 30 | 66.7 | 58.0 | +8.7 | 0.361 | +7.1 | +13.8 |
| BOS gate + sweep | 37 | 73.0 | 57.9 | +15.1 | 0.071 | +11.2 | +24.4 |
| BOS gate + FVG + with trend | 146 | 63.0 | 57.8 | +5.2 | 0.235 | +6.2 | +2.9 |
| BOS gate + FVG + discount/premium | 29 | 69.0 | 57.9 | +11.0 | 0.262 | +10.1 | +13.8 |
| BOS gate + departure >= 3 h | 210 | 60.0 | 57.9 | +2.1 | 0.569 | +2.6 | +1.3 |
| fractal BOS + FVG | 1452 | 57.4 | 58.5 | -1.1 | 0.549 | -1.4 | -0.2 |
| FVG + departure >= 3 h | 1430 | 60.4 | 56.2 | +4.2 | 0.016 | +4.9 | +2.4 |
| sweep + FVG | 555 | 59.6 | 57.7 | +1.9 | 0.426 | +1.5 | +2.9 |
| sweep + major BOS before return | 86 | 64.0 | 57.9 | +6.1 | 0.274 | +4.7 | +9.2 |
| with trend + discount/premium | 586 | 57.8 | 58.1 | -0.2 | 0.923 | +2.1 | -6.0 |
| NO major BOS (David: invalid) | 3070 | 57.9 | 59.4 | -1.5 | 0.642 | -3.3 | +1.9 |

### Criteria — v5 BITCOIN H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 42 | 64.3 | 57.8 | +6.5 | 0.435 | +5.1 | +20.6 |
| major BOS before the return (any delay) | 82 | 62.2 | 57.7 | +4.5 | 0.478 | +2.6 | +21.0 |
| zone inside any major break's move | 83 | 62.7 | 57.6 | +5.0 | 0.411 | +3.3 | +21.0 |
| the break is a CHoCH | 15 | 66.7 | 58.0 | +8.7 | 0.601 | +12.1 | -9.9 |
| BOS gate (3-bar fractal swing) | 437 | 57.7 | 58.7 | -1.0 | 0.779 | -1.1 | -1.3 |
| displacement >= 2 x avg body | 608 | 59.0 | 55.4 | +3.7 | 0.372 | +2.4 | +6.6 |
| displacement >= 3 x avg body | 335 | 57.9 | 58.3 | -0.4 | 0.941 | +1.0 | -3.8 |
| FVG in the leg-out | 626 | 58.5 | 57.0 | +1.5 | 0.738 | -2.9 | +11.8 |
| FVG >= 0.3 ATR | 379 | 57.8 | 58.4 | -0.6 | 0.884 | -4.5 | +8.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 331 | 56.8 | 59.0 | -2.2 | 0.563 | -5.7 | +6.2 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 643 | 58.3 | 57.4 | +0.9 | 0.853 | +3.8 | -6.7 |
| base >= 3 candles | 169 | 57.4 | 58.3 | -0.9 | 0.863 | -3.8 | +6.7 |
| departure >= 3 zone heights before the return | 403 | 58.1 | 58.2 | -0.1 | 1.000 | +0.7 | -2.0 |
| departure >= 2 ATR before the return | 465 | 58.3 | 57.9 | +0.4 | 0.947 | +0.5 | +0.1 |
| leg-out candle range >= 2 zone heights | 453 | 56.5 | 60.2 | -3.7 | 0.313 | -3.1 | -5.0 |
| zone height <= 0.5 ATR | 110 | 56.4 | 58.4 | -2.0 | 0.753 | +7.4 | -21.1 |
| zone height > 1 ATR | 184 | 60.9 | 57.3 | +3.5 | 0.400 | +0.4 | +9.9 |
| with the major trend | 404 | 60.4 | 55.9 | +4.5 | 0.198 | +1.0 | +13.1 |
| against the major trend | 408 | 55.9 | 60.4 | -4.5 | 0.197 | -1.0 | -13.1 |
| demand in discount / supply in premium (major range) | 411 | 56.0 | 60.3 | -4.4 | 0.226 | -6.2 | -0.0 |
| ... of the last 100 bars' range | 423 | 60.0 | 56.0 | +4.0 | 0.249 | -0.8 | +15.4 |
| liquidity sweep just before the leg-out | 174 | 58.0 | 58.2 | -0.1 | 1.000 | +1.3 | -3.4 |
| round-number level in / at the zone | 302 | 57.9 | 58.2 | -0.3 | 0.941 | +0.5 | -1.7 |
| RR >= 2 to the nearest live opposing zone | 506 | 58.5 | 57.5 | +1.0 | 0.826 | +1.4 | -0.3 |
| no live opposing zone above / below | 16 | 68.8 | 57.9 | +10.8 | 0.446 | +11.7 | n/a |
| returned within 50 bars | 679 | 57.7 | 60.2 | -2.4 | 0.625 | -0.5 | -9.1 |
| returned after > 200 bars | 50 | 56.0 | 58.3 | -2.3 | 0.775 | -6.8 | +26.7 |
| formed in Asia (00-07 UTC) | 222 | 53.6 | 59.8 | -6.2 | 0.118 | -6.1 | -6.7 |
| formed in London (07-12 UTC) | 203 | 64.0 | 56.2 | +7.9 | 0.055 | +9.1 | +5.0 |
| formed in London/NY overlap (12-16 UTC) | 174 | 63.2 | 56.7 | +6.5 | 0.146 | +5.9 | +8.4 |
| BOS gate + FVG | 42 | 64.3 | 57.8 | +6.5 | 0.435 | +5.1 | +20.6 |
| BOS gate + FVG kept | 35 | 60.0 | 58.0 | +2.0 | 0.854 | -0.8 | +20.6 |
| BOS gate + with trend | 27 | 63.0 | 58.0 | +5.0 | 0.693 | +1.0 | +40.7 |
| BOS gate + discount/premium | 4 | 75.0 | 58.0 | +17.0 | n/a | +9.3 | +40.3 |
| BOS gate + sweep | 5 | 60.0 | 58.1 | +1.9 | 1.000 | +2.6 | n/a |
| BOS gate + FVG + with trend | 27 | 63.0 | 58.0 | +5.0 | 0.693 | +1.0 | +40.7 |
| BOS gate + FVG + discount/premium | 4 | 75.0 | 58.0 | +17.0 | n/a | +9.3 | +40.3 |
| BOS gate + departure >= 3 h | 36 | 66.7 | 57.7 | +8.9 | 0.316 | +7.5 | +20.6 |
| fractal BOS + FVG | 372 | 57.8 | 58.4 | -0.6 | 0.882 | -1.0 | -0.0 |
| FVG + departure >= 3 h | 368 | 57.6 | 58.6 | -0.9 | 0.830 | -0.8 | -1.4 |
| sweep + FVG | 141 | 58.9 | 58.0 | +0.9 | 0.856 | +1.4 | -0.4 |
| sweep + major BOS before return | 18 | 66.7 | 57.9 | +8.7 | 0.491 | +7.5 | +40.3 |
| with trend + discount/premium | 187 | 59.4 | 57.8 | +1.6 | 0.733 | -2.0 | +8.1 |
| NO major BOS (David: invalid) | 770 | 57.8 | 64.3 | -6.5 | 0.424 | -5.1 | -20.6 |

## Overview — base zones

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL FX+GOLD base | 18707 | 57.5 | 57.3 | +0.2 [-0.5, +1.1] | 55.5 | 51.6 | 52.2 | 46.2 | 46.1 | 5 | 1.54 | 55.8 |
| FX+GOLD base M15 | 14881 | 57.0 | 57.2 | -0.2 [-1.1, +0.8] | 55.2 | 50.8 | 52.0 | 45.5 | 45.9 | 5 | 1.55 | 56.5 |
| FX+GOLD base H1 | 3826 | 59.6 | 57.8 | +1.8 [+0.1, +3.6] | 56.6 | 54.9 | 53.3 | 48.6 | 46.6 | 6 | 1.54 | 52.8 |
| GOLD M15 base | 3007 | 55.6 | 57.2 | -1.6 [-3.6, +0.4] | 53.5 | 50.1 | 52.7 | 45.2 | 46.1 | 6 | 1.53 | 56.6 |
| GOLD H1 base | 746 | 58.7 | 53.3 | +5.4 [+1.3, +9.5] | 54.6 | 54.6 | 48.6 | 49.1 | 43.5 | 6 | 1.53 | 52.0 |
| EURUSD M15 base | 3047 | 57.0 | 56.8 | +0.1 [-1.9, +2.2] | 55.4 | 51.0 | 51.5 | 45.5 | 45.4 | 5 | 1.51 | 56.5 |
| EURUSD H1 base | 773 | 58.1 | 57.4 | +0.7 [-3.5, +4.7] | 58.1 | 53.7 | 53.9 | 45.8 | 46.1 | 6 | 1.58 | 55.5 |
| GBPUSD M15 base | 3034 | 57.1 | 56.8 | +0.2 [-1.8, +2.2] | 55.5 | 50.6 | 52.0 | 45.0 | 45.6 | 5 | 1.56 | 57.2 |
| GBPUSD H1 base | 785 | 60.5 | 58.7 | +1.8 [-2.1, +5.8] | 55.8 | 56.8 | 54.8 | 49.4 | 46.6 | 5 | 1.56 | 52.0 |
| USDJPY M15 base | 2848 | 58.0 | 56.9 | +1.1 [-1.0, +3.2] | 55.3 | 51.6 | 51.4 | 45.8 | 45.8 | 5 | 1.57 | 56.2 |
| USDJPY H1 base | 762 | 58.3 | 58.1 | +0.2 [-3.8, +4.3] | 56.4 | 53.0 | 52.6 | 48.0 | 47.6 | 5 | 1.57 | 53.5 |
| AUDUSD M15 base | 2945 | 57.5 | 58.0 | -0.6 [-2.5, +1.5] | 56.1 | 50.6 | 52.3 | 46.1 | 46.6 | 5 | 1.55 | 56.1 |
| AUDUSD H1 base | 760 | 62.4 | 61.3 | +1.1 [-2.9, +5.1] | 58.3 | 56.4 | 56.4 | 50.8 | 49.4 | 6 | 1.45 | 51.2 |
| BITCOIN M15 base | 2927 | 56.6 | 57.5 | -0.9 [-3.0, +1.2] | 55.2 | 49.8 | 51.9 | 44.7 | 46.5 | 6 | 1.62 | 57.6 |
| BITCOIN H1 base | 737 | 56.9 | 59.4 | -2.5 [-6.6, +1.6] | 57.6 | 49.9 | 55.2 | 44.4 | 48.2 | 6 | 1.64 | 57.8 |

### In-sample / out-of-sample — base

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX+GOLD base IS | 13229 | 57.5 | 57.5 | +0.0 [-1.0, +1.0] | 55.6 | 51.4 | 52.4 | 46.1 | 46.1 | 5 | 1.54 | 55.9 |
| FX+GOLD base M15 IS | 10486 | 57.0 | 57.5 | -0.5 [-1.6, +0.6] | 55.4 | 50.6 | 52.2 | 45.5 | 46.1 | 5 | 1.53 | 56.6 |
| FX+GOLD base H1 IS | 2743 | 59.6 | 57.7 | +1.9 [-0.1, +4.0] | 56.3 | 54.7 | 53.1 | 48.3 | 46.3 | 6 | 1.55 | 53.3 |
| FX+GOLD base OOS | 5478 | 57.6 | 56.7 | +0.8 [-0.7, +2.4] | 55.1 | 52.0 | 52.0 | 46.4 | 45.9 | 5 | 1.56 | 55.4 |
| FX+GOLD base M15 OOS | 4395 | 57.1 | 56.4 | +0.7 [-1.0, +2.4] | 54.6 | 51.2 | 51.5 | 45.7 | 45.5 | 5 | 1.57 | 56.3 |
| FX+GOLD base H1 OOS | 1083 | 59.6 | 58.0 | +1.6 [-1.8, +4.8] | 57.3 | 55.5 | 54.0 | 49.4 | 47.4 | 5 | 1.50 | 51.8 |

### Base type — base

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RBR M15 | 3703 | 57.3 | 57.2 | +0.1 [-1.6, +1.8] | 55.2 | 51.0 | 52.0 | 46.4 | 45.9 | 6 | 1.60 | 55.7 |
| RBR H1 | 970 | 62.0 | 57.8 | +4.2 [+1.0, +7.5] | 56.6 | 56.8 | 53.3 | 51.1 | 46.6 | 6 | 1.57 | 51.1 |
| DBR M15 | 3676 | 57.4 | 57.2 | +0.2 [-1.5, +1.9] | 55.2 | 52.1 | 52.0 | 45.6 | 45.9 | 5 | 1.59 | 56.1 |
| DBR H1 | 911 | 59.1 | 57.8 | +1.3 [-2.1, +4.5] | 56.6 | 54.9 | 53.3 | 49.2 | 46.6 | 6 | 1.58 | 51.8 |
| DBD M15 | 3714 | 56.1 | 57.2 | -1.1 [-2.7, +0.6] | 55.2 | 49.3 | 52.0 | 43.8 | 45.9 | 5 | 1.50 | 58.3 |
| DBD H1 | 943 | 56.6 | 57.8 | -1.1 [-4.5, +2.3] | 56.6 | 52.4 | 53.3 | 45.1 | 46.6 | 6 | 1.49 | 55.8 |
| RBD M15 | 3788 | 57.3 | 57.2 | +0.1 [-1.5, +1.7] | 55.2 | 50.7 | 52.0 | 46.3 | 45.9 | 5 | 1.51 | 56.1 |
| RBD H1 | 1002 | 60.6 | 57.8 | +2.8 [-0.3, +5.9] | 56.6 | 55.5 | 53.3 | 49.0 | 46.6 | 5 | 1.51 | 52.7 |

### Freshness — base (first vs second return, FX+GOLD)

| set | first return hold % | zones that held then returned | second return hold % |
|---|---|---|---|
| base M15 | 57.0 | 8336 | 56.7 |
| base H1 | 59.6 | 2229 | 59.5 |
| base GOLD M15 | 55.6 | 1637 | 56.8 |
| base GOLD H1 | 58.7 | 421 | 59.1 |
| base EURUSD M15 | 57.0 | 1703 | 57.1 |
| base EURUSD H1 | 58.1 | 438 | 55.5 |
| base GBPUSD M15 | 57.1 | 1703 | 57.1 |
| base GBPUSD H1 | 60.5 | 470 | 58.1 |
| base USDJPY M15 | 58.0 | 1629 | 54.9 |
| base USDJPY H1 | 58.3 | 436 | 61.2 |
| base AUDUSD M15 | 57.5 | 1664 | 57.2 |
| base AUDUSD H1 | 62.4 | 464 | 63.4 |
| base BITCOIN M15 | 56.6 | 1620 | 55.8 |
| base BITCOIN H1 | 56.9 | 412 | 56.1 |

### Hold rate by age / height / departure — base FX+GOLD (zones vs matched controls)

| bars to return | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-10 | 11771 | 57.0 | 32544 | 57.4 | -0.3 |
| 10-30 | 3138 | 59.4 | 10800 | 58.3 | +1.1 |
| 30-100 | 1927 | 59.6 | 6721 | 57.7 | +2.0 |
| 100-300 | 1015 | 56.7 | 3270 | 55.4 | +1.2 |
| 300-3001 | 856 | 54.2 | 2673 | 53.6 | +0.6 |

| height / ATR | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 0-0.5 | 6109 | 55.0 | 18327 | 53.8 | +1.2 |
| 0.5-1 | 9152 | 58.9 | 27450 | 59.5 | -0.7 |
| 1-2 | 3358 | 58.6 | 9988 | 57.5 | +1.2 |
| 2-100 | 88 | 54.5 | 243 | 59.3 | -4.7 |

| departure / height | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-2 | 4803 | 58.8 | 11992 | 58.6 | +0.2 |
| 2-3 | 3340 | 58.1 | 10274 | 58.2 | -0.1 |
| 3-5 | 3735 | 58.3 | 12147 | 58.9 | -0.6 |
| 5-10 | 3427 | 56.9 | 11043 | 56.7 | +0.3 |
| 10-1000 | 3401 | 55.0 | 10552 | 53.6 | +1.3 |

### Criteria — base M15, FX+GOLD pooled (hold = 1 zone height before a close beyond distal)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1432 | 54.2 | 57.3 | -3.1 | 0.025 | -2.3 | -5.4 |
| major BOS before the return (any delay) | 2264 | 55.4 | 57.3 | -1.9 | 0.090 | -1.7 | -2.6 |
| zone inside any major break's move | 2321 | 55.4 | 57.3 | -1.9 | 0.093 | -1.7 | -2.5 |
| the break is a CHoCH | 506 | 57.3 | 57.0 | +0.3 | 0.897 | +0.7 | -0.8 |
| BOS gate (3-bar fractal swing) | 6363 | 56.0 | 57.8 | -1.7 | 0.029 | -1.6 | -2.1 |
| displacement >= 2 x avg body | 9934 | 56.4 | 58.2 | -1.8 | 0.035 | -1.8 | -1.9 |
| displacement >= 3 x avg body | 4391 | 55.8 | 57.5 | -1.7 | 0.069 | -2.1 | -0.6 |
| FVG in the leg-out | 9808 | 57.8 | 55.5 | +2.3 | 0.007 | +2.2 | +2.4 |
| FVG >= 0.3 ATR | 6420 | 57.4 | 56.7 | +0.7 | 0.416 | +0.6 | +0.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 4226 | 58.0 | 56.6 | +1.3 | 0.134 | +1.4 | +1.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 11605 | 56.5 | 58.9 | -2.4 | 0.019 | -1.8 | -3.8 |
| base >= 3 candles | 3276 | 58.9 | 56.5 | +2.4 | 0.016 | +1.8 | +3.8 |
| departure >= 3 zone heights before the return | 8401 | 56.3 | 57.9 | -1.6 | 0.045 | -1.1 | -2.8 |
| departure >= 2 ATR before the return | 7817 | 57.2 | 56.9 | +0.3 | 0.721 | +0.7 | -0.6 |
| leg-out candle range >= 2 zone heights | 8820 | 56.0 | 58.5 | -2.6 | 0.003 | -2.3 | -3.3 |
| zone height <= 0.5 ATR | 4866 | 54.4 | 58.3 | -3.9 | <0.001 | -2.7 | -6.7 |
| zone height > 1 ATR | 2698 | 57.9 | 56.8 | +1.1 | 0.283 | +0.9 | +1.5 |
| with the major trend | 7483 | 56.4 | 57.7 | -1.3 | 0.106 | -1.5 | -0.8 |
| against the major trend | 7387 | 57.7 | 56.3 | +1.4 | 0.093 | +1.6 | +0.8 |
| demand in discount / supply in premium (major range) | 7514 | 57.8 | 56.2 | +1.6 | 0.047 | +0.8 | +3.5 |
| ... of the last 100 bars' range | 7601 | 57.7 | 56.3 | +1.4 | 0.084 | +1.1 | +2.1 |
| liquidity sweep just before the leg-out | 3010 | 58.2 | 56.7 | +1.5 | 0.161 | +0.7 | +3.3 |
| round-number level in / at the zone | 2712 | 57.1 | 57.0 | +0.1 | 0.946 | +1.3 | -3.2 |
| RR >= 2 to the nearest live opposing zone | 10796 | 57.1 | 56.7 | +0.4 | 0.650 | +1.9 | -3.1 |
| no live opposing zone above / below | 454 | 54.4 | 57.1 | -2.7 | 0.274 | -2.9 | -1.4 |
| returned within 50 bars | 12618 | 57.0 | 56.9 | +0.2 | 0.888 | -0.6 | +2.2 |
| returned after > 200 bars | 907 | 53.6 | 57.2 | -3.7 | 0.029 | -2.4 | -7.7 |
| formed in Asia (00-07 UTC) | 4811 | 57.2 | 56.9 | +0.3 | 0.695 | +0.1 | +0.8 |
| formed in London (07-12 UTC) | 3195 | 58.2 | 56.7 | +1.5 | 0.142 | +1.5 | +1.6 |
| formed in London/NY overlap (12-16 UTC) | 2727 | 57.3 | 57.0 | +0.3 | 0.759 | -0.2 | +1.8 |
| BOS gate + FVG | 1162 | 53.7 | 57.3 | -3.6 | 0.018 | -2.7 | -6.4 |
| BOS gate + FVG kept | 735 | 53.6 | 57.2 | -3.6 | 0.053 | -2.9 | -5.6 |
| BOS gate + with trend | 923 | 52.7 | 57.3 | -4.6 | 0.004 | -3.6 | -7.7 |
| BOS gate + discount/premium | 165 | 56.4 | 57.0 | -0.7 | 0.881 | -3.5 | +8.8 |
| BOS gate + sweep | 168 | 57.1 | 57.0 | +0.1 | 1.000 | +0.8 | -1.5 |
| BOS gate + FVG + with trend | 741 | 51.1 | 57.3 | -6.2 | 0.002 | -4.8 | -10.3 |
| BOS gate + FVG + discount/premium | 141 | 57.4 | 57.0 | +0.4 | 0.927 | -1.1 | +6.3 |
| BOS gate + departure >= 3 h | 1182 | 53.6 | 57.3 | -3.8 | 0.010 | -2.9 | -6.4 |
| fractal BOS + FVG | 4815 | 56.8 | 57.1 | -0.3 | 0.718 | -0.4 | -0.1 |
| FVG + departure >= 3 h | 6518 | 57.2 | 56.9 | +0.3 | 0.724 | +0.3 | +0.3 |
| sweep + FVG | 2048 | 58.5 | 56.8 | +1.8 | 0.135 | +1.2 | +3.4 |
| sweep + major BOS before return | 359 | 55.7 | 57.0 | -1.3 | 0.623 | -1.6 | -0.6 |
| with trend + discount/premium | 2241 | 57.3 | 57.0 | +0.4 | 0.749 | -0.8 | +2.9 |
| NO major BOS (David: invalid) | 13449 | 57.3 | 54.2 | +3.1 | 0.029 | +2.3 | +5.4 |

### Criteria — base M15, FX+GOLD pooled, hold = 1 ATR

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1432 | 49.2 | 50.9 | -1.7 | 0.219 | -0.8 | -4.2 |
| major BOS before the return (any delay) | 2264 | 50.2 | 50.9 | -0.7 | 0.555 | -0.4 | -1.4 |
| zone inside any major break's move | 2321 | 50.3 | 50.9 | -0.6 | 0.635 | -0.2 | -1.4 |
| the break is a CHoCH | 506 | 53.6 | 50.7 | +2.9 | 0.200 | +3.7 | +0.4 |
| BOS gate (3-bar fractal swing) | 6363 | 50.4 | 51.0 | -0.6 | 0.506 | -0.7 | -0.1 |
| displacement >= 2 x avg body | 9934 | 50.9 | 50.5 | +0.4 | 0.636 | -0.0 | +1.5 |
| displacement >= 3 x avg body | 4391 | 50.7 | 50.8 | -0.1 | 0.887 | -0.6 | +1.0 |
| FVG in the leg-out | 9808 | 52.5 | 47.5 | +5.0 | <0.001 | +4.7 | +5.7 |
| FVG >= 0.3 ATR | 6420 | 52.5 | 49.4 | +3.1 | <0.001 | +2.5 | +4.6 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 4226 | 54.0 | 49.5 | +4.5 | <0.001 | +4.2 | +5.4 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 11605 | 49.0 | 57.2 | -8.2 | <0.001 | -7.4 | -10.2 |
| base >= 3 candles | 3276 | 57.2 | 49.0 | +8.2 | <0.001 | +7.4 | +10.2 |
| departure >= 3 zone heights before the return | 8401 | 48.4 | 53.8 | -5.4 | <0.001 | -5.3 | -5.7 |
| departure >= 2 ATR before the return | 7817 | 51.9 | 49.5 | +2.5 | 0.003 | +2.2 | +3.0 |
| leg-out candle range >= 2 zone heights | 8820 | 46.7 | 56.7 | -10.0 | <0.001 | -9.4 | -11.6 |
| zone height <= 0.5 ATR | 4866 | 42.9 | 54.6 | -11.7 | <0.001 | -10.5 | -14.4 |
| zone height > 1 ATR | 2698 | 60.6 | 48.6 | +12.0 | <0.001 | +11.6 | +13.0 |
| with the major trend | 7483 | 49.7 | 51.9 | -2.2 | 0.010 | -2.4 | -1.7 |
| against the major trend | 7387 | 51.9 | 49.7 | +2.2 | 0.007 | +2.4 | +1.7 |
| demand in discount / supply in premium (major range) | 7514 | 52.1 | 49.4 | +2.7 | 0.001 | +2.0 | +4.4 |
| ... of the last 100 bars' range | 7601 | 52.0 | 49.5 | +2.5 | 0.003 | +2.4 | +2.7 |
| liquidity sweep just before the leg-out | 3010 | 53.5 | 50.1 | +3.4 | 0.002 | +2.8 | +4.8 |
| round-number level in / at the zone | 2712 | 53.4 | 50.2 | +3.2 | 0.002 | +4.1 | +0.9 |
| RR >= 2 to the nearest live opposing zone | 10796 | 49.3 | 54.5 | -5.2 | <0.001 | -4.1 | -7.9 |
| no live opposing zone above / below | 454 | 47.4 | 50.9 | -3.5 | 0.155 | -3.9 | -1.2 |
| returned within 50 bars | 12618 | 50.3 | 53.4 | -3.1 | 0.008 | -2.7 | -4.2 |
| returned after > 200 bars | 907 | 49.1 | 50.9 | -1.8 | 0.302 | -1.1 | -3.9 |
| formed in Asia (00-07 UTC) | 4811 | 50.9 | 50.7 | +0.2 | 0.801 | +0.3 | +0.1 |
| formed in London (07-12 UTC) | 3195 | 51.1 | 50.7 | +0.5 | 0.646 | +0.3 | +0.8 |
| formed in London/NY overlap (12-16 UTC) | 2727 | 53.1 | 50.3 | +2.8 | 0.008 | +2.4 | +3.8 |
| BOS gate + FVG | 1162 | 49.0 | 50.9 | -2.0 | 0.208 | -1.0 | -4.7 |
| BOS gate + FVG kept | 735 | 48.7 | 50.9 | -2.2 | 0.247 | -1.3 | -4.8 |
| BOS gate + with trend | 923 | 47.0 | 51.0 | -4.0 | 0.017 | -3.1 | -6.4 |
| BOS gate + discount/premium | 165 | 53.9 | 50.7 | +3.2 | 0.440 | +1.4 | +9.4 |
| BOS gate + sweep | 168 | 54.8 | 50.7 | +4.0 | 0.323 | +3.1 | +6.7 |
| BOS gate + FVG + with trend | 741 | 45.7 | 51.0 | -5.3 | 0.006 | -4.3 | -8.1 |
| BOS gate + FVG + discount/premium | 141 | 55.3 | 50.7 | +4.6 | 0.299 | +4.4 | +5.5 |
| BOS gate + departure >= 3 h | 1182 | 47.6 | 51.0 | -3.4 | 0.025 | -2.6 | -5.8 |
| fractal BOS + FVG | 4815 | 51.8 | 50.3 | +1.5 | 0.100 | +1.0 | +2.7 |
| FVG + departure >= 3 h | 6518 | 50.1 | 51.3 | -1.2 | 0.145 | -1.5 | -0.4 |
| sweep + FVG | 2048 | 54.3 | 50.2 | +4.1 | <0.001 | +3.6 | +5.7 |
| sweep + major BOS before return | 359 | 51.3 | 50.8 | +0.5 | 0.883 | -0.4 | +3.2 |
| with trend + discount/premium | 2241 | 51.8 | 50.6 | +1.2 | 0.300 | +0.0 | +3.6 |
| NO major BOS (David: invalid) | 13449 | 50.9 | 49.2 | +1.7 | 0.223 | +0.8 | +4.2 |

### Criteria — base M15, FX+GOLD pooled, hold = 2 zone heights (RR 2)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1432 | 43.6 | 45.7 | -2.2 | 0.127 | -1.2 | -4.8 |
| major BOS before the return (any delay) | 2264 | 45.5 | 45.5 | +0.0 | 1.000 | +0.3 | -0.8 |
| zone inside any major break's move | 2321 | 45.5 | 45.5 | -0.1 | 0.944 | +0.3 | -1.1 |
| the break is a CHoCH | 506 | 46.2 | 45.5 | +0.7 | 0.747 | +2.3 | -3.7 |
| BOS gate (3-bar fractal swing) | 6363 | 45.0 | 45.9 | -0.9 | 0.273 | -0.9 | -0.8 |
| displacement >= 2 x avg body | 9934 | 45.3 | 46.0 | -0.7 | 0.395 | -1.3 | +0.6 |
| displacement >= 3 x avg body | 4391 | 45.0 | 45.7 | -0.7 | 0.447 | -1.3 | +0.8 |
| FVG in the leg-out | 9808 | 46.2 | 44.3 | +1.9 | 0.028 | +1.8 | +2.2 |
| FVG >= 0.3 ATR | 6420 | 46.1 | 45.1 | +1.1 | 0.187 | +0.6 | +2.3 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 4226 | 47.0 | 44.9 | +2.1 | 0.017 | +2.2 | +1.9 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 11605 | 45.8 | 44.6 | +1.2 | 0.213 | +1.2 | +1.2 |
| base >= 3 candles | 3276 | 44.6 | 45.8 | -1.2 | 0.215 | -1.2 | -1.2 |
| departure >= 3 zone heights before the return | 8401 | 47.3 | 43.2 | +4.1 | <0.001 | +4.5 | +3.2 |
| departure >= 2 ATR before the return | 7817 | 46.7 | 44.2 | +2.4 | 0.002 | +2.6 | +2.1 |
| leg-out candle range >= 2 zone heights | 8820 | 46.9 | 43.6 | +3.3 | <0.001 | +3.5 | +2.7 |
| zone height <= 0.5 ATR | 4866 | 47.9 | 44.3 | +3.6 | <0.001 | +4.5 | +1.4 |
| zone height > 1 ATR | 2698 | 42.2 | 46.3 | -4.1 | <0.001 | -4.6 | -2.8 |
| with the major trend | 7483 | 45.1 | 45.9 | -0.8 | 0.312 | -1.4 | +0.6 |
| against the major trend | 7387 | 46.0 | 45.1 | +0.9 | 0.282 | +1.5 | -0.6 |
| demand in discount / supply in premium (major range) | 7514 | 46.8 | 44.3 | +2.5 | 0.003 | +1.8 | +4.3 |
| ... of the last 100 bars' range | 7601 | 46.6 | 44.4 | +2.3 | 0.007 | +1.9 | +3.1 |
| liquidity sweep just before the leg-out | 3010 | 45.3 | 45.6 | -0.3 | 0.785 | -0.6 | +0.6 |
| round-number level in / at the zone | 2712 | 44.8 | 45.7 | -0.8 | 0.428 | +0.5 | -4.4 |
| RR >= 2 to the nearest live opposing zone | 10796 | 46.6 | 42.7 | +3.8 | <0.001 | +4.8 | +1.4 |
| no live opposing zone above / below | 454 | 43.2 | 45.6 | -2.4 | 0.317 | -2.3 | -2.9 |
| returned within 50 bars | 12618 | 45.3 | 46.8 | -1.6 | 0.175 | -1.8 | -1.0 |
| returned after > 200 bars | 907 | 45.4 | 45.5 | -0.1 | 0.975 | +0.1 | -0.6 |
| formed in Asia (00-07 UTC) | 4811 | 45.8 | 45.4 | +0.4 | 0.632 | -0.1 | +1.6 |
| formed in London (07-12 UTC) | 3195 | 46.1 | 45.4 | +0.7 | 0.481 | +0.7 | +0.8 |
| formed in London/NY overlap (12-16 UTC) | 2727 | 44.1 | 45.8 | -1.7 | 0.108 | -2.0 | -1.0 |
| BOS gate + FVG | 1162 | 43.0 | 45.7 | -2.7 | 0.077 | -1.8 | -5.4 |
| BOS gate + FVG kept | 735 | 43.8 | 45.6 | -1.8 | 0.344 | -1.2 | -3.8 |
| BOS gate + with trend | 923 | 42.3 | 45.7 | -3.5 | 0.038 | -2.9 | -5.2 |
| BOS gate + discount/premium | 165 | 43.6 | 45.5 | -1.9 | 0.639 | -3.0 | +1.7 |
| BOS gate + sweep | 168 | 44.6 | 45.5 | -0.9 | 0.875 | -2.4 | +3.3 |
| BOS gate + FVG + with trend | 741 | 40.5 | 45.8 | -5.3 | 0.006 | -4.6 | -7.5 |
| BOS gate + FVG + discount/premium | 141 | 44.7 | 45.5 | -0.8 | 0.858 | -1.3 | +1.0 |
| BOS gate + departure >= 3 h | 1182 | 43.5 | 45.7 | -2.2 | 0.142 | -1.5 | -4.5 |
| fractal BOS + FVG | 4815 | 45.8 | 45.4 | +0.4 | 0.678 | -0.1 | +1.6 |
| FVG + departure >= 3 h | 6518 | 47.7 | 43.8 | +4.0 | <0.001 | +3.8 | +4.3 |
| sweep + FVG | 2048 | 45.3 | 45.6 | -0.3 | 0.813 | -0.6 | +0.6 |
| sweep + major BOS before return | 359 | 46.0 | 45.5 | +0.5 | 0.876 | -0.9 | +4.4 |
| with trend + discount/premium | 2241 | 47.1 | 45.2 | +1.8 | 0.110 | +0.5 | +4.6 |
| NO major BOS (David: invalid) | 13449 | 45.7 | 43.6 | +2.2 | 0.132 | +1.2 | +4.8 |

### Criteria — base H1, FX+GOLD pooled (hold = 1 zone height before a close beyond distal)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 413 | 60.5 | 59.5 | +1.1 | 0.709 | +1.2 | +0.5 |
| major BOS before the return (any delay) | 641 | 60.4 | 59.4 | +0.9 | 0.658 | +1.6 | -1.5 |
| zone inside any major break's move | 655 | 60.5 | 59.4 | +1.0 | 0.640 | +1.6 | -1.0 |
| the break is a CHoCH | 155 | 63.9 | 59.4 | +4.5 | 0.268 | +4.0 | +6.3 |
| BOS gate (3-bar fractal swing) | 1723 | 60.0 | 59.2 | +0.8 | 0.642 | +1.4 | -0.9 |
| displacement >= 2 x avg body | 2726 | 60.1 | 58.3 | +1.9 | 0.294 | +3.1 | -1.2 |
| displacement >= 3 x avg body | 1285 | 61.3 | 58.7 | +2.6 | 0.119 | +3.6 | +0.2 |
| FVG in the leg-out | 2444 | 60.1 | 58.7 | +1.4 | 0.391 | +1.4 | +1.6 |
| FVG >= 0.3 ATR | 1592 | 60.5 | 59.0 | +1.5 | 0.347 | +2.8 | -1.6 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1093 | 59.9 | 59.5 | +0.5 | 0.794 | +1.8 | -2.9 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3015 | 58.8 | 62.5 | -3.7 | 0.053 | -4.2 | -2.4 |
| base >= 3 candles | 811 | 62.5 | 58.8 | +3.7 | 0.059 | +4.2 | +2.4 |
| departure >= 3 zone heights before the return | 2163 | 58.6 | 60.9 | -2.2 | 0.169 | -2.2 | -2.2 |
| departure >= 2 ATR before the return | 2034 | 59.7 | 59.5 | +0.2 | 0.924 | +0.9 | -1.5 |
| leg-out candle range >= 2 zone heights | 2354 | 58.8 | 60.8 | -2.0 | 0.231 | -1.7 | -2.5 |
| zone height <= 0.5 ATR | 1243 | 57.2 | 60.7 | -3.5 | 0.034 | -3.9 | -2.6 |
| zone height > 1 ATR | 747 | 60.6 | 59.3 | +1.3 | 0.542 | +1.0 | +2.0 |
| with the major trend | 1905 | 59.7 | 59.5 | +0.2 | 0.919 | -1.8 | +5.3 |
| against the major trend | 1917 | 59.5 | 59.7 | -0.1 | 0.952 | +1.9 | -5.3 |
| demand in discount / supply in premium (major range) | 1933 | 59.3 | 59.9 | -0.5 | 0.766 | -0.0 | -1.7 |
| ... of the last 100 bars' range | 1910 | 59.1 | 60.1 | -1.1 | 0.519 | -1.0 | -1.2 |
| liquidity sweep just before the leg-out | 724 | 58.6 | 59.8 | -1.3 | 0.550 | -0.4 | -3.8 |
| round-number level in / at the zone | 1236 | 59.5 | 59.6 | -0.1 | 0.976 | +1.2 | -3.5 |
| RR >= 2 to the nearest live opposing zone | 2665 | 59.5 | 59.8 | -0.3 | 0.883 | -0.1 | -0.6 |
| no live opposing zone above / below | 176 | 57.4 | 59.7 | -2.3 | 0.578 | -1.4 | -7.7 |
| returned within 50 bars | 3253 | 59.9 | 58.1 | +1.7 | 0.456 | +0.4 | +6.0 |
| returned after > 200 bars | 225 | 56.0 | 59.8 | -3.8 | 0.268 | -2.1 | -9.1 |
| formed in Asia (00-07 UTC) | 1403 | 58.4 | 60.3 | -1.9 | 0.246 | -1.6 | -2.8 |
| formed in London (07-12 UTC) | 984 | 62.1 | 58.7 | +3.4 | 0.065 | +3.2 | +3.9 |
| formed in London/NY overlap (12-16 UTC) | 716 | 59.1 | 59.7 | -0.6 | 0.776 | -1.4 | +1.4 |
| BOS gate + FVG | 341 | 58.7 | 59.7 | -1.0 | 0.730 | -1.0 | -1.2 |
| BOS gate + FVG kept | 223 | 60.1 | 59.6 | +0.5 | 0.898 | +1.9 | -4.0 |
| BOS gate + with trend | 257 | 58.8 | 59.7 | -0.9 | 0.783 | -0.3 | -2.8 |
| BOS gate + discount/premium | 46 | 58.7 | 59.6 | -0.9 | 1.000 | +0.4 | -5.1 |
| BOS gate + sweep | 50 | 64.0 | 59.5 | +4.5 | 0.558 | +2.9 | +10.5 |
| BOS gate + FVG + with trend | 213 | 58.2 | 59.7 | -1.5 | 0.706 | -0.5 | -4.7 |
| BOS gate + FVG + discount/premium | 40 | 60.0 | 59.6 | +0.4 | 1.000 | +0.4 | +0.4 |
| BOS gate + departure >= 3 h | 335 | 57.9 | 59.8 | -1.8 | 0.527 | -2.7 | +1.1 |
| fractal BOS + FVG | 1278 | 60.7 | 59.0 | +1.7 | 0.318 | +2.5 | -0.4 |
| FVG + departure >= 3 h | 1653 | 58.4 | 60.5 | -2.1 | 0.187 | -1.7 | -3.2 |
| sweep + FVG | 494 | 60.5 | 59.5 | +1.1 | 0.661 | +1.5 | -0.2 |
| sweep + major BOS before return | 110 | 60.9 | 59.6 | +1.4 | 0.849 | +0.6 | +4.2 |
| with trend + discount/premium | 538 | 60.0 | 59.5 | +0.5 | 0.857 | -1.2 | +4.8 |
| NO major BOS (David: invalid) | 3413 | 59.5 | 60.5 | -1.1 | 0.697 | -1.2 | -0.5 |

### Criteria — base H1, FX+GOLD pooled, hold = 1 ATR

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 413 | 56.4 | 54.7 | +1.7 | 0.530 | +1.9 | +1.3 |
| major BOS before the return (any delay) | 641 | 56.0 | 54.7 | +1.3 | 0.538 | +2.1 | -1.2 |
| zone inside any major break's move | 655 | 56.2 | 54.7 | +1.5 | 0.499 | +2.2 | -0.5 |
| the break is a CHoCH | 155 | 60.6 | 54.7 | +6.0 | 0.152 | +6.6 | +4.0 |
| BOS gate (3-bar fractal swing) | 1723 | 55.8 | 54.2 | +1.6 | 0.353 | +2.5 | -0.9 |
| displacement >= 2 x avg body | 2726 | 55.8 | 52.6 | +3.2 | 0.071 | +4.8 | -0.5 |
| displacement >= 3 x avg body | 1285 | 56.4 | 54.2 | +2.3 | 0.197 | +3.1 | +0.2 |
| FVG in the leg-out | 2444 | 55.6 | 53.8 | +1.8 | 0.290 | +2.2 | +0.7 |
| FVG >= 0.3 ATR | 1592 | 56.5 | 53.8 | +2.7 | 0.097 | +4.1 | -1.0 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1093 | 56.1 | 54.4 | +1.6 | 0.371 | +2.9 | -1.7 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3015 | 53.2 | 61.4 | -8.2 | <0.001 | -9.4 | -5.2 |
| base >= 3 candles | 811 | 61.4 | 53.2 | +8.2 | <0.001 | +9.4 | +5.2 |
| departure >= 3 zone heights before the return | 2163 | 51.9 | 58.9 | -7.0 | <0.001 | -7.6 | -5.5 |
| departure >= 2 ATR before the return | 2034 | 55.8 | 53.9 | +1.9 | 0.238 | +1.9 | +1.8 |
| leg-out candle range >= 2 zone heights | 2354 | 51.7 | 60.0 | -8.2 | <0.001 | -8.5 | -7.7 |
| zone height <= 0.5 ATR | 1243 | 48.2 | 58.1 | -10.0 | <0.001 | -11.2 | -6.8 |
| zone height > 1 ATR | 747 | 64.0 | 52.7 | +11.3 | <0.001 | +11.3 | +11.4 |
| with the major trend | 1905 | 54.5 | 55.3 | -0.8 | 0.601 | -2.8 | +4.0 |
| against the major trend | 1917 | 55.3 | 54.5 | +0.9 | 0.603 | +2.8 | -4.0 |
| demand in discount / supply in premium (major range) | 1933 | 54.7 | 55.2 | -0.5 | 0.794 | +0.2 | -2.1 |
| ... of the last 100 bars' range | 1910 | 54.4 | 55.4 | -1.0 | 0.541 | -0.3 | -3.0 |
| liquidity sweep just before the leg-out | 724 | 56.5 | 54.5 | +1.9 | 0.362 | +2.5 | +0.4 |
| round-number level in / at the zone | 1236 | 56.0 | 54.4 | +1.6 | 0.369 | +3.1 | -2.4 |
| RR >= 2 to the nearest live opposing zone | 2665 | 53.2 | 58.8 | -5.6 | 0.002 | -6.2 | -4.2 |
| no live opposing zone above / below | 176 | 54.5 | 54.9 | -0.4 | 0.935 | -0.4 | +0.5 |
| returned within 50 bars | 3253 | 55.1 | 53.8 | +1.4 | 0.557 | +0.2 | +4.6 |
| returned after > 200 bars | 225 | 53.8 | 55.0 | -1.2 | 0.742 | +1.9 | -10.6 |
| formed in Asia (00-07 UTC) | 1403 | 53.7 | 55.6 | -2.0 | 0.247 | -1.9 | -2.0 |
| formed in London (07-12 UTC) | 984 | 57.6 | 54.0 | +3.6 | 0.049 | +3.2 | +4.6 |
| formed in London/NY overlap (12-16 UTC) | 716 | 57.5 | 54.3 | +3.2 | 0.125 | +3.3 | +3.1 |
| BOS gate + FVG | 341 | 54.0 | 55.0 | -1.0 | 0.739 | -1.0 | -1.0 |
| BOS gate + FVG kept | 223 | 55.2 | 54.9 | +0.3 | 0.948 | +2.2 | -5.8 |
| BOS gate + with trend | 257 | 54.1 | 55.0 | -0.9 | 0.792 | -1.0 | -0.3 |
| BOS gate + discount/premium | 46 | 52.2 | 54.9 | -2.8 | 0.761 | +2.5 | -19.3 |
| BOS gate + sweep | 50 | 64.0 | 54.8 | +9.2 | 0.199 | +7.9 | +14.6 |
| BOS gate + FVG + with trend | 213 | 53.5 | 55.0 | -1.5 | 0.723 | -1.1 | -2.5 |
| BOS gate + FVG + discount/premium | 40 | 52.5 | 54.9 | -2.4 | 0.877 | +2.0 | -15.6 |
| BOS gate + departure >= 3 h | 335 | 52.5 | 55.1 | -2.6 | 0.399 | -3.1 | -0.6 |
| fractal BOS + FVG | 1278 | 56.5 | 54.1 | +2.4 | 0.171 | +3.7 | -1.0 |
| FVG + departure >= 3 h | 1653 | 51.7 | 57.4 | -5.7 | <0.001 | -5.3 | -6.7 |
| sweep + FVG | 494 | 58.5 | 54.4 | +4.1 | 0.088 | +4.4 | +3.4 |
| sweep + major BOS before return | 110 | 60.9 | 54.7 | +6.2 | 0.209 | +5.7 | +8.3 |
| with trend + discount/premium | 538 | 54.5 | 55.0 | -0.5 | 0.854 | -2.5 | +4.4 |
| NO major BOS (David: invalid) | 3413 | 54.7 | 56.4 | -1.7 | 0.542 | -1.9 | -1.3 |

### Criteria — base H1, FX+GOLD pooled, hold = 2 zone heights (RR 2)

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 413 | 49.4 | 48.5 | +0.9 | 0.754 | +0.3 | +3.1 |
| major BOS before the return (any delay) | 641 | 50.5 | 48.2 | +2.3 | 0.289 | +2.9 | +0.7 |
| zone inside any major break's move | 655 | 50.5 | 48.2 | +2.3 | 0.293 | +2.9 | +0.7 |
| the break is a CHoCH | 155 | 53.5 | 48.4 | +5.1 | 0.211 | +3.9 | +10.3 |
| BOS gate (3-bar fractal swing) | 1723 | 49.3 | 48.0 | +1.3 | 0.431 | +1.8 | +0.2 |
| displacement >= 2 x avg body | 2726 | 48.7 | 48.5 | +0.2 | 0.911 | +2.1 | -4.1 |
| displacement >= 3 x avg body | 1285 | 48.4 | 48.7 | -0.3 | 0.872 | -0.0 | -1.1 |
| FVG in the leg-out | 2444 | 48.7 | 48.4 | +0.3 | 0.876 | +1.5 | -2.5 |
| FVG >= 0.3 ATR | 1592 | 48.6 | 48.7 | -0.1 | 0.970 | +1.5 | -4.2 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1093 | 49.7 | 48.2 | +1.5 | 0.423 | +3.3 | -3.0 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3015 | 49.1 | 47.0 | +2.1 | 0.315 | +1.7 | +2.9 |
| base >= 3 candles | 811 | 47.0 | 49.1 | -2.1 | 0.307 | -1.7 | -2.9 |
| departure >= 3 zone heights before the return | 2163 | 49.6 | 47.4 | +2.2 | 0.182 | +1.9 | +2.7 |
| departure >= 2 ATR before the return | 2034 | 49.3 | 47.8 | +1.5 | 0.362 | +2.9 | -2.0 |
| leg-out candle range >= 2 zone heights | 2354 | 49.8 | 46.7 | +3.0 | 0.064 | +3.3 | +2.2 |
| zone height <= 0.5 ATR | 1243 | 51.6 | 47.2 | +4.4 | 0.008 | +3.5 | +6.5 |
| zone height > 1 ATR | 747 | 44.6 | 49.6 | -5.0 | 0.013 | -5.3 | -4.3 |
| with the major trend | 1905 | 48.5 | 48.7 | -0.2 | 0.899 | -2.8 | +6.2 |
| against the major trend | 1917 | 48.7 | 48.5 | +0.2 | 0.900 | +2.8 | -6.2 |
| demand in discount / supply in premium (major range) | 1933 | 47.8 | 49.4 | -1.6 | 0.320 | +0.0 | -5.8 |
| ... of the last 100 bars' range | 1910 | 47.6 | 49.6 | -1.9 | 0.231 | -0.3 | -6.2 |
| liquidity sweep just before the leg-out | 724 | 47.0 | 49.0 | -2.0 | 0.347 | -2.1 | -1.6 |
| round-number level in / at the zone | 1236 | 47.7 | 49.0 | -1.3 | 0.472 | -0.8 | -2.4 |
| RR >= 2 to the nearest live opposing zone | 2665 | 49.5 | 46.7 | +2.8 | 0.126 | +2.5 | +3.2 |
| no live opposing zone above / below | 176 | 46.6 | 48.7 | -2.1 | 0.585 | -0.7 | -9.6 |
| returned within 50 bars | 3253 | 48.7 | 48.3 | +0.3 | 0.895 | -0.2 | +1.8 |
| returned after > 200 bars | 225 | 48.4 | 48.6 | -0.2 | 1.000 | +2.4 | -8.0 |
| formed in Asia (00-07 UTC) | 1403 | 48.4 | 48.7 | -0.3 | 0.846 | +0.2 | -1.7 |
| formed in London (07-12 UTC) | 984 | 51.0 | 47.8 | +3.2 | 0.085 | +3.1 | +3.3 |
| formed in London/NY overlap (12-16 UTC) | 716 | 46.2 | 49.2 | -2.9 | 0.159 | -2.1 | -5.1 |
| BOS gate + FVG | 341 | 48.1 | 48.7 | -0.6 | 0.859 | -1.1 | +1.3 |
| BOS gate + FVG kept | 223 | 48.0 | 48.7 | -0.7 | 0.891 | +0.2 | -3.4 |
| BOS gate + with trend | 257 | 47.1 | 48.7 | -1.6 | 0.651 | -1.7 | -1.2 |
| BOS gate + discount/premium | 46 | 43.5 | 48.7 | -5.2 | 0.555 | -2.6 | -13.2 |
| BOS gate + sweep | 50 | 52.0 | 48.6 | +3.4 | 0.678 | +1.7 | +10.7 |
| BOS gate + FVG + with trend | 213 | 47.9 | 48.7 | -0.8 | 0.827 | -0.1 | -2.6 |
| BOS gate + FVG + discount/premium | 40 | 42.5 | 48.7 | -6.2 | 0.531 | -5.0 | -9.5 |
| BOS gate + departure >= 3 h | 335 | 47.8 | 48.7 | -0.9 | 0.775 | -1.9 | +2.9 |
| fractal BOS + FVG | 1278 | 50.2 | 47.8 | +2.3 | 0.186 | +3.6 | -1.0 |
| FVG + departure >= 3 h | 1653 | 48.9 | 48.4 | +0.6 | 0.743 | +0.9 | -0.3 |
| sweep + FVG | 494 | 49.0 | 48.6 | +0.4 | 0.883 | -0.1 | +2.1 |
| sweep + major BOS before return | 110 | 52.7 | 48.5 | +4.2 | 0.398 | +4.1 | +5.3 |
| with trend + discount/premium | 538 | 48.0 | 48.7 | -0.8 | 0.764 | -3.1 | +4.8 |
| NO major BOS (David: invalid) | 3413 | 48.5 | 49.4 | -0.9 | 0.760 | -0.3 | -3.1 |

### Criteria — base GOLD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 337 | 54.9 | 55.7 | -0.8 | 0.822 | -0.2 | -2.0 |
| major BOS before the return (any delay) | 541 | 53.6 | 56.0 | -2.4 | 0.309 | -2.5 | -2.3 |
| zone inside any major break's move | 557 | 53.7 | 56.0 | -2.4 | 0.321 | -2.6 | -1.6 |
| the break is a CHoCH | 123 | 57.7 | 55.5 | +2.2 | 0.638 | +6.1 | -5.2 |
| BOS gate (3-bar fractal swing) | 1291 | 55.5 | 55.7 | -0.1 | 0.966 | +2.4 | -6.6 |
| displacement >= 2 x avg body | 2025 | 54.4 | 58.1 | -3.8 | 0.056 | -5.6 | +0.2 |
| displacement >= 3 x avg body | 950 | 54.8 | 56.0 | -1.1 | 0.570 | -0.7 | -2.4 |
| FVG in the leg-out | 2002 | 55.7 | 55.4 | +0.3 | 0.913 | +0.4 | -0.3 |
| FVG >= 0.3 ATR | 1307 | 55.5 | 55.6 | -0.1 | 0.968 | +1.0 | -3.0 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 881 | 55.3 | 55.7 | -0.5 | 0.842 | +1.3 | -5.2 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2312 | 55.6 | 55.5 | +0.1 | 1.000 | +0.4 | -0.6 |
| base >= 3 candles | 695 | 55.5 | 55.6 | -0.1 | 1.000 | -0.4 | +0.6 |
| departure >= 3 zone heights before the return | 1729 | 55.4 | 55.9 | -0.5 | 0.817 | -1.1 | +1.2 |
| departure >= 2 ATR before the return | 1633 | 54.9 | 56.5 | -1.6 | 0.378 | +0.7 | -7.3 |
| leg-out candle range >= 2 zone heights | 1796 | 54.6 | 57.1 | -2.6 | 0.163 | -4.4 | +1.8 |
| zone height <= 0.5 ATR | 942 | 53.5 | 56.6 | -3.1 | 0.126 | -4.8 | +1.2 |
| zone height > 1 ATR | 547 | 54.8 | 55.8 | -0.9 | 0.699 | +0.2 | -2.9 |
| with the major trend | 1504 | 55.6 | 55.6 | -0.0 | 1.000 | -1.4 | +3.1 |
| against the major trend | 1501 | 55.6 | 55.6 | +0.1 | 1.000 | +1.4 | -3.1 |
| demand in discount / supply in premium (major range) | 1548 | 55.7 | 55.5 | +0.2 | 0.945 | -0.7 | +2.2 |
| ... of the last 100 bars' range | 1569 | 57.3 | 53.8 | +3.5 | 0.050 | +3.7 | +2.9 |
| liquidity sweep just before the leg-out | 601 | 54.6 | 55.9 | -1.3 | 0.592 | -0.9 | -2.4 |
| round-number level in / at the zone | 1644 | 57.1 | 53.8 | +3.3 | 0.072 | +5.2 | -1.1 |
| RR >= 2 to the nearest live opposing zone | 2158 | 56.0 | 54.7 | +1.3 | 0.513 | +1.4 | +1.7 |
| no live opposing zone above / below | 108 | 58.3 | 55.5 | +2.8 | 0.609 | +2.1 | n/a |
| returned within 50 bars | 2511 | 56.3 | 52.2 | +4.1 | 0.093 | +4.1 | +4.0 |
| returned after > 200 bars | 194 | 51.0 | 55.9 | -4.9 | 0.209 | -4.2 | -7.1 |
| formed in Asia (00-07 UTC) | 938 | 57.6 | 54.7 | +2.9 | 0.155 | +1.3 | +6.6 |
| formed in London (07-12 UTC) | 684 | 55.3 | 55.7 | -0.4 | 0.867 | +0.9 | -3.8 |
| formed in London/NY overlap (12-16 UTC) | 556 | 59.4 | 54.8 | +4.6 | 0.050 | +5.5 | +2.2 |
| BOS gate + FVG | 268 | 53.4 | 55.8 | -2.5 | 0.447 | -0.9 | -6.2 |
| BOS gate + FVG kept | 170 | 52.9 | 55.8 | -2.8 | 0.485 | -3.2 | -1.8 |
| BOS gate + with trend | 214 | 53.3 | 55.8 | -2.5 | 0.518 | -3.7 | +0.3 |
| BOS gate + discount/premium | 41 | 56.1 | 55.6 | +0.5 | 1.000 | -4.6 | +10.7 |
| BOS gate + sweep | 39 | 56.4 | 55.6 | +0.8 | 1.000 | +4.5 | -3.8 |
| BOS gate + FVG + with trend | 169 | 50.3 | 55.9 | -5.6 | 0.181 | -5.0 | -7.2 |
| BOS gate + FVG + discount/premium | 34 | 55.9 | 55.6 | +0.3 | 1.000 | -1.8 | +4.7 |
| BOS gate + departure >= 3 h | 281 | 53.4 | 55.8 | -2.5 | 0.440 | -2.3 | -2.8 |
| fractal BOS + FVG | 970 | 55.9 | 55.5 | +0.4 | 0.846 | +2.5 | -5.3 |
| FVG + departure >= 3 h | 1357 | 54.9 | 56.2 | -1.3 | 0.501 | -2.1 | +0.5 |
| sweep + FVG | 417 | 54.0 | 55.9 | -1.9 | 0.473 | -0.8 | -5.3 |
| sweep + major BOS before return | 78 | 50.0 | 55.8 | -5.8 | 0.357 | -1.7 | -14.1 |
| with trend + discount/premium | 453 | 57.0 | 55.4 | +1.6 | 0.533 | -0.6 | +7.2 |
| NO major BOS (David: invalid) | 2670 | 55.7 | 54.9 | +0.8 | 0.815 | +0.2 | +2.0 |

### Criteria — base GOLD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 42 | 59.5 | 58.7 | +0.9 | 1.000 | -1.5 | +4.8 |
| major BOS before the return (any delay) | 73 | 60.3 | 58.5 | +1.7 | 0.812 | +0.6 | +4.5 |
| zone inside any major break's move | 74 | 60.8 | 58.5 | +2.3 | 0.717 | +0.6 | +6.6 |
| the break is a CHoCH | 11 | 63.6 | 58.6 | +5.0 | 0.774 | +1.1 | +14.4 |
| BOS gate (3-bar fractal swing) | 325 | 58.2 | 59.1 | -1.0 | 0.823 | -2.9 | +5.0 |
| displacement >= 2 x avg body | 502 | 59.8 | 56.6 | +3.2 | 0.440 | +2.8 | +2.9 |
| displacement >= 3 x avg body | 214 | 58.9 | 58.6 | +0.2 | 1.000 | -1.0 | +3.8 |
| FVG in the leg-out | 472 | 60.2 | 56.2 | +4.0 | 0.318 | +1.1 | +10.6 |
| FVG >= 0.3 ATR | 308 | 60.4 | 57.5 | +2.9 | 0.470 | +0.9 | +7.0 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 204 | 60.3 | 58.1 | +2.2 | 0.619 | +3.0 | +2.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 567 | 58.7 | 58.7 | +0.1 | 1.000 | -0.4 | +1.9 |
| base >= 3 candles | 179 | 58.7 | 58.7 | -0.1 | 1.000 | +0.4 | -1.9 |
| departure >= 3 zone heights before the return | 435 | 60.0 | 56.9 | +3.1 | 0.398 | +1.7 | +7.7 |
| departure >= 2 ATR before the return | 387 | 61.5 | 55.7 | +5.8 | 0.118 | +2.6 | +13.5 |
| leg-out candle range >= 2 zone heights | 477 | 59.3 | 57.6 | +1.7 | 0.702 | +1.9 | +4.5 |
| zone height <= 0.5 ATR | 263 | 58.9 | 58.6 | +0.3 | 0.933 | +2.3 | -1.4 |
| zone height > 1 ATR | 124 | 54.8 | 59.5 | -4.6 | 0.380 | -3.5 | -14.0 |
| with the major trend | 374 | 59.6 | 57.8 | +1.8 | 0.668 | -0.5 | +7.5 |
| against the major trend | 370 | 57.8 | 59.6 | -1.7 | 0.654 | +0.7 | -7.5 |
| demand in discount / supply in premium (major range) | 378 | 57.4 | 60.1 | -2.6 | 0.507 | -0.5 | -8.3 |
| ... of the last 100 bars' range | 367 | 55.9 | 61.5 | -5.6 | 0.137 | -7.3 | -0.6 |
| liquidity sweep just before the leg-out | 125 | 58.4 | 58.8 | -0.4 | 1.000 | +3.5 | -9.3 |
| round-number level in / at the zone | 626 | 58.3 | 60.8 | -2.5 | 0.605 | +0.2 | -7.4 |
| RR >= 2 to the nearest live opposing zone | 519 | 60.5 | 54.6 | +5.9 | 0.152 | +7.7 | +7.5 |
| no live opposing zone above / below | 39 | 61.5 | 58.6 | +3.0 | 0.733 | +0.1 | n/a |
| returned within 50 bars | 638 | 59.1 | 56.5 | +2.6 | 0.662 | +5.7 | -4.4 |
| returned after > 200 bars | 42 | 52.4 | 59.1 | -6.7 | 0.416 | -6.6 | -6.7 |
| formed in Asia (00-07 UTC) | 245 | 58.0 | 59.1 | -1.1 | 0.812 | -1.1 | -1.6 |
| formed in London (07-12 UTC) | 201 | 59.7 | 58.3 | +1.4 | 0.798 | +4.6 | -3.5 |
| formed in London/NY overlap (12-16 UTC) | 131 | 61.8 | 58.0 | +3.8 | 0.432 | -0.8 | +15.0 |
| BOS gate + FVG | 29 | 58.6 | 58.7 | -0.1 | 1.000 | -5.1 | +14.6 |
| BOS gate + FVG kept | 19 | 63.2 | 58.6 | +4.6 | 0.796 | -1.5 | +23.0 |
| BOS gate + with trend | 30 | 60.0 | 58.7 | +1.3 | 1.000 | +0.1 | -2.5 |
| BOS gate + discount/premium | 2 | 0.0 | 58.9 | -58.9 | n/a | -61.7 | n/a |
| BOS gate + sweep | 2 | 100.0 | 58.6 | +41.4 | n/a | +38.7 | n/a |
| BOS gate + FVG + with trend | 21 | 57.1 | 58.8 | -1.6 | 1.000 | -6.1 | +14.4 |
| BOS gate + FVG + discount/premium | 1 | 0.0 | 58.8 | -58.8 | n/a | -61.5 | n/a |
| BOS gate + departure >= 3 h | 35 | 54.3 | 58.9 | -4.6 | 0.604 | -8.3 | +4.8 |
| fractal BOS + FVG | 230 | 62.2 | 57.2 | +5.0 | 0.227 | +3.7 | +9.1 |
| FVG + departure >= 3 h | 324 | 60.8 | 57.1 | +3.7 | 0.323 | +2.6 | +7.1 |
| sweep + FVG | 85 | 61.2 | 58.4 | +2.8 | 0.639 | +5.3 | -2.8 |
| sweep + major BOS before return | 12 | 66.7 | 58.6 | +8.1 | 0.766 | +16.6 | -19.4 |
| with trend + discount/premium | 95 | 62.1 | 58.2 | +3.9 | 0.501 | +2.2 | +4.1 |
| NO major BOS (David: invalid) | 704 | 58.7 | 59.5 | -0.9 | 1.000 | +1.5 | -4.8 |

### Criteria — base EURUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 273 | 54.9 | 57.2 | -2.2 | 0.489 | -1.7 | -3.6 |
| major BOS before the return (any delay) | 459 | 55.1 | 57.3 | -2.2 | 0.404 | -0.8 | -5.7 |
| zone inside any major break's move | 466 | 55.2 | 57.3 | -2.2 | 0.417 | -0.7 | -5.8 |
| the break is a CHoCH | 88 | 62.5 | 56.8 | +5.7 | 0.336 | +3.8 | +10.5 |
| BOS gate (3-bar fractal swing) | 1324 | 56.3 | 57.5 | -1.1 | 0.552 | -0.5 | -2.5 |
| displacement >= 2 x avg body | 2034 | 57.5 | 56.0 | +1.5 | 0.430 | +1.5 | +1.6 |
| displacement >= 3 x avg body | 873 | 57.5 | 56.8 | +0.7 | 0.721 | -0.2 | +2.8 |
| FVG in the leg-out | 1970 | 57.1 | 56.8 | +0.2 | 0.910 | +1.3 | -2.2 |
| FVG >= 0.3 ATR | 1264 | 57.7 | 56.5 | +1.2 | 0.541 | +2.0 | -0.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 856 | 57.1 | 56.9 | +0.2 | 0.937 | +1.2 | -2.3 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2370 | 56.2 | 59.8 | -3.7 | 0.097 | -3.6 | -3.6 |
| base >= 3 candles | 677 | 59.8 | 56.2 | +3.7 | 0.098 | +3.6 | +3.6 |
| departure >= 3 zone heights before the return | 1702 | 55.2 | 59.3 | -4.1 | 0.026 | -3.2 | -6.0 |
| departure >= 2 ATR before the return | 1549 | 57.6 | 56.3 | +1.2 | 0.506 | +1.8 | -0.1 |
| leg-out candle range >= 2 zone heights | 1803 | 56.0 | 58.4 | -2.5 | 0.191 | -2.4 | -2.6 |
| zone height <= 0.5 ATR | 984 | 53.2 | 58.8 | -5.6 | 0.003 | -4.7 | -7.8 |
| zone height > 1 ATR | 572 | 57.7 | 56.8 | +0.9 | 0.705 | +2.1 | -2.1 |
| with the major trend | 1532 | 55.7 | 58.3 | -2.6 | 0.152 | -3.9 | +0.5 |
| against the major trend | 1511 | 58.4 | 55.6 | +2.8 | 0.128 | +4.1 | -0.5 |
| demand in discount / supply in premium (major range) | 1504 | 57.8 | 56.2 | +1.6 | 0.396 | +1.5 | +1.8 |
| ... of the last 100 bars' range | 1551 | 57.5 | 56.4 | +1.1 | 0.572 | +1.5 | +0.1 |
| liquidity sweep just before the leg-out | 582 | 60.1 | 56.2 | +3.9 | 0.097 | +3.3 | +5.4 |
| round-number level in / at the zone | 225 | 52.0 | 57.4 | -5.4 | 0.119 | -3.1 | -12.2 |
| RR >= 2 to the nearest live opposing zone | 2248 | 57.9 | 54.4 | +3.4 | 0.093 | +5.0 | -0.2 |
| no live opposing zone above / below | 50 | 48.0 | 57.1 | -9.1 | 0.252 | -13.1 | -2.3 |
| returned within 50 bars | 2545 | 57.1 | 56.4 | +0.7 | 0.762 | -1.3 | +6.0 |
| returned after > 200 bars | 193 | 53.4 | 57.2 | -3.9 | 0.311 | -2.2 | -9.5 |
| formed in Asia (00-07 UTC) | 994 | 58.2 | 56.4 | +1.9 | 0.323 | +2.1 | +1.5 |
| formed in London (07-12 UTC) | 672 | 57.7 | 56.8 | +1.0 | 0.659 | -1.6 | +6.6 |
| formed in London/NY overlap (12-16 UTC) | 565 | 54.7 | 57.5 | -2.8 | 0.238 | -1.2 | -7.0 |
| BOS gate + FVG | 227 | 53.7 | 57.2 | -3.5 | 0.327 | -2.7 | -5.6 |
| BOS gate + FVG kept | 126 | 54.0 | 57.1 | -3.1 | 0.536 | +0.4 | -12.8 |
| BOS gate + with trend | 184 | 51.6 | 57.3 | -5.7 | 0.146 | -3.8 | -10.3 |
| BOS gate + discount/premium | 28 | 64.3 | 56.9 | +7.4 | 0.452 | +3.4 | +17.4 |
| BOS gate + sweep | 30 | 66.7 | 56.9 | +9.8 | 0.365 | +8.1 | +11.6 |
| BOS gate + FVG + with trend | 152 | 50.7 | 57.3 | -6.6 | 0.114 | -4.7 | -12.2 |
| BOS gate + FVG + discount/premium | 23 | 60.9 | 56.9 | +3.9 | 0.846 | +4.5 | +2.2 |
| BOS gate + departure >= 3 h | 225 | 54.2 | 57.2 | -3.0 | 0.406 | -1.4 | -7.4 |
| fractal BOS + FVG | 1006 | 56.9 | 57.0 | -0.2 | 0.946 | +0.6 | -2.1 |
| FVG + departure >= 3 h | 1314 | 55.9 | 57.8 | -2.0 | 0.294 | -0.2 | -6.1 |
| sweep + FVG | 381 | 59.6 | 56.6 | +3.0 | 0.299 | +3.1 | +2.7 |
| sweep + major BOS before return | 66 | 60.6 | 56.9 | +3.7 | 0.622 | +3.4 | +4.2 |
| with trend + discount/premium | 408 | 56.1 | 57.1 | -1.0 | 0.743 | -2.5 | +3.1 |
| NO major BOS (David: invalid) | 2774 | 57.2 | 54.9 | +2.2 | 0.484 | +1.7 | +3.6 |

### Criteria — base EURUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 92 | 60.9 | 57.7 | +3.2 | 0.577 | +4.6 | -1.3 |
| major BOS before the return (any delay) | 140 | 60.7 | 57.5 | +3.2 | 0.523 | +5.5 | -5.5 |
| zone inside any major break's move | 142 | 60.6 | 57.5 | +3.0 | 0.512 | +4.8 | -3.2 |
| the break is a CHoCH | 38 | 63.2 | 57.8 | +5.3 | 0.611 | +6.7 | +0.0 |
| BOS gate (3-bar fractal swing) | 358 | 59.5 | 56.9 | +2.6 | 0.456 | +5.6 | -5.0 |
| displacement >= 2 x avg body | 573 | 59.2 | 55.0 | +4.2 | 0.329 | +4.8 | +2.5 |
| displacement >= 3 x avg body | 288 | 60.8 | 56.5 | +4.3 | 0.253 | +9.4 | -9.5 |
| FVG in the leg-out | 495 | 58.8 | 56.8 | +2.0 | 0.642 | +4.5 | -4.9 |
| FVG >= 0.3 ATR | 331 | 58.3 | 57.9 | +0.4 | 0.943 | +2.4 | -5.0 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 242 | 59.9 | 57.3 | +2.7 | 0.531 | +6.6 | -8.0 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 621 | 57.0 | 62.5 | -5.5 | 0.233 | -10.4 | +10.1 |
| base >= 3 candles | 152 | 62.5 | 57.0 | +5.5 | 0.235 | +10.4 | -10.1 |
| departure >= 3 zone heights before the return | 438 | 57.5 | 58.8 | -1.3 | 0.768 | +2.5 | -11.2 |
| departure >= 2 ATR before the return | 428 | 57.2 | 59.1 | -1.9 | 0.613 | +2.4 | -13.6 |
| leg-out candle range >= 2 zone heights | 477 | 57.9 | 58.4 | -0.6 | 0.883 | +0.2 | -2.4 |
| zone height <= 0.5 ATR | 236 | 55.1 | 59.4 | -4.3 | 0.270 | -5.7 | +0.5 |
| zone height > 1 ATR | 168 | 57.7 | 58.2 | -0.4 | 0.927 | -0.4 | -0.5 |
| with the major trend | 388 | 59.0 | 57.1 | +1.9 | 0.621 | +0.6 | +5.0 |
| against the major trend | 383 | 57.2 | 59.0 | -1.8 | 0.677 | -0.5 | -5.0 |
| demand in discount / supply in premium (major range) | 396 | 55.6 | 60.7 | -5.2 | 0.146 | -6.5 | -1.9 |
| ... of the last 100 bars' range | 373 | 56.8 | 59.2 | -2.4 | 0.526 | +0.1 | -8.8 |
| liquidity sweep just before the leg-out | 158 | 55.1 | 58.9 | -3.8 | 0.418 | -4.2 | -2.0 |
| round-number level in / at the zone | 120 | 59.2 | 57.9 | +1.3 | 0.832 | +2.4 | -1.9 |
| RR >= 2 to the nearest live opposing zone | 529 | 57.8 | 58.6 | -0.8 | 0.864 | -1.7 | +1.7 |
| no live opposing zone above / below | 42 | 57.1 | 58.1 | -1.0 | 1.000 | +1.3 | -6.6 |
| returned within 50 bars | 659 | 58.7 | 54.4 | +4.3 | 0.404 | -1.6 | +26.4 |
| returned after > 200 bars | 40 | 47.5 | 58.7 | -11.2 | 0.195 | -3.0 | -47.3 |
| formed in Asia (00-07 UTC) | 286 | 55.6 | 59.5 | -4.0 | 0.286 | -3.1 | -6.6 |
| formed in London (07-12 UTC) | 223 | 60.1 | 57.3 | +2.8 | 0.524 | +2.3 | +4.1 |
| formed in London/NY overlap (12-16 UTC) | 139 | 59.7 | 57.7 | +2.0 | 0.695 | +1.3 | +3.9 |
| BOS gate + FVG | 79 | 59.5 | 57.9 | +1.6 | 0.805 | +3.3 | -4.1 |
| BOS gate + FVG kept | 50 | 54.0 | 58.4 | -4.4 | 0.554 | +0.1 | -21.0 |
| BOS gate + with trend | 54 | 59.3 | 58.0 | +1.3 | 0.886 | +2.3 | -1.8 |
| BOS gate + discount/premium | 14 | 57.1 | 58.1 | -1.0 | 1.000 | +15.7 | -60.9 |
| BOS gate + sweep | 14 | 64.3 | 58.0 | +6.3 | 0.776 | +4.3 | +40.2 |
| BOS gate + FVG + with trend | 45 | 57.8 | 58.1 | -0.3 | 1.000 | +1.5 | -5.8 |
| BOS gate + FVG + discount/premium | 13 | 61.5 | 58.0 | +3.5 | 1.000 | +23.0 | -60.9 |
| BOS gate + departure >= 3 h | 77 | 61.0 | 57.8 | +3.3 | 0.648 | +5.8 | -6.6 |
| fractal BOS + FVG | 269 | 60.2 | 56.9 | +3.3 | 0.409 | +8.3 | -10.4 |
| FVG + departure >= 3 h | 333 | 57.4 | 58.6 | -1.3 | 0.777 | +2.6 | -11.7 |
| sweep + FVG | 110 | 54.5 | 58.7 | -4.1 | 0.457 | -2.4 | -9.1 |
| sweep + major BOS before return | 23 | 60.9 | 58.0 | +2.9 | 0.836 | -0.2 | +40.4 |
| with trend + discount/premium | 125 | 56.0 | 58.5 | -2.5 | 0.619 | -2.8 | -2.8 |
| NO major BOS (David: invalid) | 681 | 57.7 | 60.9 | -3.2 | 0.574 | -4.6 | +1.3 |

### Criteria — base GBPUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 274 | 49.6 | 57.8 | -8.2 | 0.011 | -6.3 | -12.9 |
| major BOS before the return (any delay) | 426 | 53.3 | 57.7 | -4.4 | 0.090 | -4.2 | -4.6 |
| zone inside any major break's move | 438 | 53.2 | 57.7 | -4.5 | 0.087 | -4.3 | -4.6 |
| the break is a CHoCH | 102 | 51.0 | 57.3 | -6.3 | 0.218 | -6.0 | -6.6 |
| BOS gate (3-bar fractal swing) | 1279 | 55.4 | 58.3 | -2.9 | 0.107 | -4.8 | +1.5 |
| displacement >= 2 x avg body | 1991 | 57.0 | 57.1 | -0.1 | 0.972 | -0.2 | +0.1 |
| displacement >= 3 x avg body | 878 | 56.8 | 57.1 | -0.3 | 0.913 | -1.0 | +1.4 |
| FVG in the leg-out | 2013 | 58.5 | 54.2 | +4.4 | 0.025 | +2.7 | +8.2 |
| FVG >= 0.3 ATR | 1321 | 56.9 | 57.2 | -0.4 | 0.853 | -1.7 | +2.8 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 847 | 60.2 | 55.8 | +4.4 | 0.029 | +3.3 | +7.2 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2361 | 56.0 | 60.9 | -5.0 | 0.020 | -3.5 | -8.1 |
| base >= 3 candles | 673 | 60.9 | 56.0 | +5.0 | 0.023 | +3.5 | +8.1 |
| departure >= 3 zone heights before the return | 1656 | 56.5 | 57.8 | -1.3 | 0.492 | -0.6 | -2.9 |
| departure >= 2 ATR before the return | 1550 | 57.5 | 56.5 | +1.0 | 0.587 | +0.6 | +2.1 |
| leg-out candle range >= 2 zone heights | 1751 | 55.5 | 59.2 | -3.8 | 0.041 | -2.9 | -5.6 |
| zone height <= 0.5 ATR | 984 | 53.7 | 58.7 | -5.0 | 0.012 | -3.9 | -7.5 |
| zone height > 1 ATR | 581 | 60.9 | 56.1 | +4.8 | 0.035 | +4.2 | +6.5 |
| with the major trend | 1530 | 56.6 | 57.5 | -0.9 | 0.639 | -0.3 | -2.2 |
| against the major trend | 1502 | 57.5 | 56.6 | +0.9 | 0.596 | +0.3 | +2.2 |
| demand in discount / supply in premium (major range) | 1525 | 58.6 | 55.5 | +3.0 | 0.102 | +1.6 | +5.9 |
| ... of the last 100 bars' range | 1517 | 57.4 | 56.8 | +0.6 | 0.778 | -1.3 | +4.6 |
| liquidity sweep just before the leg-out | 653 | 61.7 | 55.8 | +5.9 | 0.009 | +5.6 | +6.5 |
| round-number level in / at the zone | 313 | 55.9 | 57.2 | -1.3 | 0.678 | +0.5 | -5.8 |
| RR >= 2 to the nearest live opposing zone | 2152 | 55.9 | 59.9 | -4.0 | 0.053 | -0.7 | -11.1 |
| no live opposing zone above / below | 85 | 51.8 | 57.2 | -5.4 | 0.378 | -4.9 | n/a |
| returned within 50 bars | 2601 | 56.8 | 58.7 | -1.9 | 0.513 | -2.3 | -1.1 |
| returned after > 200 bars | 185 | 51.9 | 57.4 | -5.5 | 0.154 | -3.3 | -11.0 |
| formed in Asia (00-07 UTC) | 1043 | 55.8 | 57.7 | -1.9 | 0.318 | -0.4 | -5.3 |
| formed in London (07-12 UTC) | 658 | 57.9 | 56.8 | +1.1 | 0.639 | +1.7 | -0.3 |
| formed in London/NY overlap (12-16 UTC) | 555 | 57.7 | 56.9 | +0.7 | 0.775 | -0.6 | +4.0 |
| BOS gate + FVG | 220 | 50.9 | 57.5 | -6.6 | 0.052 | -6.7 | -6.0 |
| BOS gate + FVG kept | 145 | 51.7 | 57.3 | -5.6 | 0.207 | -5.8 | -4.5 |
| BOS gate + with trend | 171 | 49.1 | 57.5 | -8.4 | 0.036 | -5.6 | -15.7 |
| BOS gate + discount/premium | 26 | 57.7 | 57.0 | +0.6 | 1.000 | +3.6 | -8.5 |
| BOS gate + sweep | 31 | 71.0 | 56.9 | +14.1 | 0.143 | +14.5 | +13.1 |
| BOS gate + FVG + with trend | 134 | 50.0 | 57.4 | -7.4 | 0.114 | -6.8 | -8.7 |
| BOS gate + FVG + discount/premium | 24 | 62.5 | 57.0 | +5.5 | 0.674 | +6.8 | +1.6 |
| BOS gate + departure >= 3 h | 224 | 51.8 | 57.5 | -5.7 | 0.104 | -4.8 | -7.9 |
| fractal BOS + FVG | 973 | 57.7 | 56.8 | +0.9 | 0.662 | -1.5 | +6.6 |
| FVG + departure >= 3 h | 1295 | 58.1 | 56.3 | +1.8 | 0.336 | +0.7 | +4.4 |
| sweep + FVG | 450 | 62.0 | 56.2 | +5.8 | 0.026 | +5.8 | +5.8 |
| sweep + major BOS before return | 72 | 63.9 | 56.9 | +7.0 | 0.273 | +6.2 | +10.5 |
| with trend + discount/premium | 432 | 58.8 | 56.8 | +2.0 | 0.432 | +0.6 | +4.2 |
| NO major BOS (David: invalid) | 2760 | 57.8 | 49.6 | +8.2 | 0.011 | +6.3 | +12.9 |

### Criteria — base GBPUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 101 | 61.4 | 60.4 | +1.0 | 0.911 | -0.3 | +5.6 |
| major BOS before the return (any delay) | 145 | 58.6 | 60.9 | -2.3 | 0.639 | -5.7 | +8.9 |
| zone inside any major break's move | 149 | 59.1 | 60.8 | -1.8 | 0.693 | -4.8 | +8.9 |
| the break is a CHoCH | 38 | 60.5 | 60.5 | +0.0 | 1.000 | -3.0 | +12.4 |
| BOS gate (3-bar fractal swing) | 352 | 59.4 | 61.4 | -2.1 | 0.605 | -2.6 | -1.1 |
| displacement >= 2 x avg body | 567 | 60.1 | 61.5 | -1.3 | 0.761 | +2.6 | -10.1 |
| displacement >= 3 x avg body | 276 | 64.1 | 58.5 | +5.6 | 0.156 | +6.4 | +3.6 |
| FVG in the leg-out | 488 | 60.5 | 60.6 | -0.2 | 1.000 | -3.9 | +9.3 |
| FVG >= 0.3 ATR | 320 | 61.6 | 59.8 | +1.8 | 0.653 | +3.3 | -1.6 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 218 | 60.6 | 60.5 | +0.1 | 1.000 | -0.9 | +2.7 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 630 | 60.0 | 62.6 | -2.6 | 0.573 | -3.6 | +0.0 |
| base >= 3 candles | 155 | 62.6 | 60.0 | +2.6 | 0.571 | +3.6 | -0.0 |
| departure >= 3 zone heights before the return | 437 | 58.1 | 63.5 | -5.4 | 0.146 | -8.2 | +1.7 |
| departure >= 2 ATR before the return | 441 | 59.9 | 61.3 | -1.5 | 0.714 | -1.6 | -0.7 |
| leg-out candle range >= 2 zone heights | 471 | 59.0 | 62.7 | -3.7 | 0.338 | -5.5 | +0.7 |
| zone height <= 0.5 ATR | 235 | 53.6 | 63.5 | -9.8 | 0.011 | -12.7 | -2.7 |
| zone height > 1 ATR | 175 | 62.3 | 60.0 | +2.3 | 0.613 | +3.6 | -1.1 |
| with the major trend | 382 | 58.6 | 62.3 | -3.6 | 0.299 | -8.6 | +8.8 |
| against the major trend | 403 | 62.3 | 58.6 | +3.6 | 0.308 | +8.6 | -8.8 |
| demand in discount / supply in premium (major range) | 415 | 60.0 | 61.1 | -1.1 | 0.767 | -1.2 | -0.2 |
| ... of the last 100 bars' range | 422 | 60.7 | 60.3 | +0.3 | 0.945 | -0.2 | +1.7 |
| liquidity sweep just before the leg-out | 156 | 59.6 | 60.7 | -1.1 | 0.850 | -2.5 | +4.3 |
| round-number level in / at the zone | 182 | 63.2 | 59.7 | +3.5 | 0.433 | +1.4 | +11.5 |
| RR >= 2 to the nearest live opposing zone | 577 | 61.2 | 58.7 | +2.5 | 0.553 | +3.3 | +0.5 |
| no live opposing zone above / below | 20 | 35.0 | 61.2 | -26.2 | 0.021 | -25.4 | n/a |
| returned within 50 bars | 655 | 60.9 | 58.5 | +2.5 | 0.617 | +3.6 | -1.7 |
| returned after > 200 bars | 52 | 67.3 | 60.0 | +7.3 | 0.310 | +5.9 | +12.6 |
| formed in Asia (00-07 UTC) | 321 | 58.9 | 61.6 | -2.8 | 0.446 | +1.6 | -13.8 |
| formed in London (07-12 UTC) | 216 | 65.7 | 58.5 | +7.2 | 0.072 | +7.3 | +6.6 |
| formed in London/NY overlap (12-16 UTC) | 162 | 56.2 | 61.6 | -5.5 | 0.214 | -8.2 | +1.7 |
| BOS gate + FVG | 82 | 58.5 | 60.7 | -2.2 | 0.717 | -4.2 | +4.0 |
| BOS gate + FVG kept | 56 | 66.1 | 60.1 | +6.0 | 0.385 | +2.6 | +16.6 |
| BOS gate + with trend | 63 | 61.9 | 60.4 | +1.5 | 0.886 | +1.5 | +1.8 |
| BOS gate + discount/premium | 13 | 53.8 | 60.6 | -6.8 | 0.768 | -14.3 | +37.3 |
| BOS gate + sweep | 20 | 65.0 | 60.4 | +4.6 | 0.820 | +0.5 | +17.3 |
| BOS gate + FVG + with trend | 50 | 60.0 | 60.5 | -0.5 | 1.000 | -1.2 | +1.3 |
| BOS gate + FVG + discount/premium | 13 | 53.8 | 60.6 | -6.8 | 0.768 | -14.3 | +37.3 |
| BOS gate + departure >= 3 h | 83 | 61.4 | 60.4 | +1.0 | 0.898 | -1.9 | +11.6 |
| fractal BOS + FVG | 256 | 59.4 | 61.1 | -1.7 | 0.700 | -4.9 | +6.7 |
| FVG + departure >= 3 h | 333 | 58.6 | 61.9 | -3.4 | 0.372 | -7.7 | +7.9 |
| sweep + FVG | 102 | 59.8 | 60.6 | -0.8 | 0.910 | -3.6 | +8.7 |
| sweep + major BOS before return | 30 | 60.0 | 60.5 | -0.5 | 1.000 | -7.4 | +15.3 |
| with trend + discount/premium | 93 | 54.8 | 61.3 | -6.4 | 0.260 | -12.5 | +17.4 |
| NO major BOS (David: invalid) | 684 | 60.4 | 61.4 | -1.0 | 0.910 | +0.3 | -5.6 |

### Criteria — base USDJPY M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 283 | 54.4 | 58.4 | -4.0 | 0.205 | -3.9 | -6.1 |
| major BOS before the return (any delay) | 421 | 57.2 | 58.1 | -0.9 | 0.752 | -1.4 | -0.1 |
| zone inside any major break's move | 431 | 57.3 | 58.1 | -0.8 | 0.752 | -1.2 | -0.3 |
| the break is a CHoCH | 104 | 52.9 | 58.2 | -5.3 | 0.309 | -6.0 | -2.5 |
| BOS gate (3-bar fractal swing) | 1232 | 57.1 | 58.7 | -1.5 | 0.434 | -2.3 | +0.5 |
| displacement >= 2 x avg body | 1925 | 56.8 | 60.6 | -3.8 | 0.062 | -3.0 | -5.8 |
| displacement >= 3 x avg body | 847 | 56.1 | 58.8 | -2.7 | 0.189 | -4.5 | +1.5 |
| FVG in the leg-out | 1891 | 58.6 | 56.7 | +1.9 | 0.341 | +2.4 | +0.6 |
| FVG >= 0.3 ATR | 1265 | 57.5 | 58.4 | -0.8 | 0.682 | -1.5 | +0.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 822 | 57.1 | 58.4 | -1.3 | 0.524 | -0.8 | -3.0 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2236 | 57.5 | 59.8 | -2.3 | 0.323 | -2.8 | -0.8 |
| base >= 3 candles | 612 | 59.8 | 57.5 | +2.3 | 0.309 | +2.8 | +0.8 |
| departure >= 3 zone heights before the return | 1625 | 57.5 | 58.6 | -1.1 | 0.567 | +0.7 | -5.5 |
| departure >= 2 ATR before the return | 1507 | 57.4 | 58.7 | -1.3 | 0.479 | -0.7 | -2.6 |
| leg-out candle range >= 2 zone heights | 1725 | 57.4 | 58.9 | -1.6 | 0.395 | -0.7 | -3.7 |
| zone height <= 0.5 ATR | 957 | 53.9 | 60.1 | -6.2 | <0.001 | -2.6 | -14.5 |
| zone height > 1 ATR | 501 | 59.9 | 57.6 | +2.3 | 0.367 | +0.3 | +7.2 |
| with the major trend | 1430 | 58.0 | 58.0 | +0.1 | 0.969 | +1.0 | -2.1 |
| against the major trend | 1416 | 58.0 | 58.0 | -0.1 | 1.000 | -0.9 | +2.1 |
| demand in discount / supply in premium (major range) | 1409 | 59.1 | 56.9 | +2.2 | 0.243 | +1.2 | +4.8 |
| ... of the last 100 bars' range | 1438 | 58.7 | 57.3 | +1.4 | 0.458 | +1.0 | +2.5 |
| liquidity sweep just before the leg-out | 545 | 59.1 | 57.8 | +1.3 | 0.600 | +0.2 | +4.2 |
| round-number level in / at the zone | 331 | 61.3 | 57.6 | +3.8 | 0.192 | +2.6 | +7.2 |
| RR >= 2 to the nearest live opposing zone | 2091 | 58.2 | 57.3 | +0.9 | 0.679 | +2.4 | -2.8 |
| no live opposing zone above / below | 120 | 53.3 | 58.2 | -4.9 | 0.310 | -7.2 | -1.3 |
| returned within 50 bars | 2424 | 58.1 | 57.5 | +0.5 | 0.874 | -1.6 | +7.4 |
| returned after > 200 bars | 177 | 58.8 | 58.0 | +0.8 | 0.872 | +2.8 | -6.1 |
| formed in Asia (00-07 UTC) | 898 | 59.7 | 57.2 | +2.5 | 0.217 | +1.3 | +5.4 |
| formed in London (07-12 UTC) | 548 | 60.6 | 57.4 | +3.2 | 0.182 | +5.1 | -1.0 |
| formed in London/NY overlap (12-16 UTC) | 513 | 58.5 | 57.9 | +0.6 | 0.848 | -1.6 | +6.8 |
| BOS gate + FVG | 229 | 54.6 | 58.3 | -3.7 | 0.296 | -3.5 | -7.2 |
| BOS gate + FVG kept | 147 | 53.1 | 58.3 | -5.2 | 0.235 | -4.8 | -9.6 |
| BOS gate + with trend | 178 | 55.6 | 58.2 | -2.5 | 0.532 | -1.8 | -7.2 |
| BOS gate + discount/premium | 40 | 55.0 | 58.0 | -3.0 | 0.754 | -4.2 | +3.0 |
| BOS gate + sweep | 29 | 55.2 | 58.0 | -2.9 | 0.853 | -0.7 | -23.7 |
| BOS gate + FVG + with trend | 142 | 54.2 | 58.2 | -4.0 | 0.384 | -2.8 | -11.8 |
| BOS gate + FVG + discount/premium | 35 | 57.1 | 58.0 | -0.9 | 1.000 | -3.6 | +18.1 |
| BOS gate + departure >= 3 h | 234 | 54.7 | 58.3 | -3.6 | 0.297 | -3.6 | -5.6 |
| fractal BOS + FVG | 923 | 56.7 | 58.6 | -2.0 | 0.329 | -2.6 | -0.5 |
| FVG + departure >= 3 h | 1263 | 58.2 | 57.9 | +0.3 | 0.888 | +1.0 | -1.3 |
| sweep + FVG | 374 | 61.2 | 57.5 | +3.7 | 0.185 | +1.2 | +10.3 |
| sweep + major BOS before return | 66 | 56.1 | 58.1 | -2.0 | 0.805 | -1.9 | -3.2 |
| with trend + discount/premium | 479 | 58.2 | 58.0 | +0.3 | 0.911 | -0.3 | +1.8 |
| NO major BOS (David: invalid) | 2565 | 58.4 | 54.4 | +4.0 | 0.215 | +3.9 | +6.1 |

### Criteria — base USDJPY H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 75 | 62.7 | 57.8 | +4.9 | 0.452 | +4.1 | +8.5 |
| major BOS before the return (any delay) | 117 | 59.8 | 58.0 | +1.8 | 0.753 | +2.1 | +1.3 |
| zone inside any major break's move | 118 | 59.3 | 58.1 | +1.2 | 0.843 | +1.4 | +1.3 |
| the break is a CHoCH | 32 | 62.5 | 58.1 | +4.4 | 0.721 | -2.2 | +27.8 |
| BOS gate (3-bar fractal swing) | 349 | 59.0 | 57.6 | +1.4 | 0.716 | +3.3 | -3.5 |
| displacement >= 2 x avg body | 524 | 58.0 | 58.8 | -0.8 | 0.874 | +2.1 | -7.6 |
| displacement >= 3 x avg body | 244 | 58.6 | 58.1 | +0.5 | 0.939 | +1.0 | -0.9 |
| FVG in the leg-out | 484 | 58.5 | 57.9 | +0.6 | 0.942 | +1.2 | -1.1 |
| FVG >= 0.3 ATR | 307 | 59.6 | 57.4 | +2.2 | 0.555 | +4.9 | -4.7 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 212 | 59.0 | 58.0 | +1.0 | 0.870 | +2.0 | -1.6 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 602 | 56.3 | 65.6 | -9.3 | 0.039 | -8.1 | -12.0 |
| base >= 3 candles | 160 | 65.6 | 56.3 | +9.3 | 0.031 | +8.1 | +12.0 |
| departure >= 3 zone heights before the return | 431 | 58.7 | 57.7 | +1.0 | 0.823 | +0.1 | +3.3 |
| departure >= 2 ATR before the return | 378 | 60.8 | 55.7 | +5.1 | 0.172 | +6.5 | +1.5 |
| leg-out candle range >= 2 zone heights | 483 | 56.9 | 60.6 | -3.6 | 0.363 | -1.5 | -9.2 |
| zone height <= 0.5 ATR | 270 | 57.4 | 58.7 | -1.3 | 0.757 | -1.6 | -0.8 |
| zone height > 1 ATR | 124 | 63.7 | 57.2 | +6.5 | 0.201 | +5.5 | +9.3 |
| with the major trend | 380 | 58.7 | 57.9 | +0.8 | 0.821 | +0.7 | +1.0 |
| against the major trend | 382 | 57.9 | 58.7 | -0.8 | 0.813 | -0.7 | -1.0 |
| demand in discount / supply in premium (major range) | 361 | 59.3 | 57.4 | +1.9 | 0.613 | -0.3 | +7.5 |
| ... of the last 100 bars' range | 356 | 58.4 | 58.1 | +0.3 | 0.945 | -1.8 | +5.6 |
| liquidity sweep just before the leg-out | 136 | 59.6 | 58.0 | +1.6 | 0.775 | +5.8 | -10.4 |
| round-number level in / at the zone | 190 | 58.9 | 58.0 | +0.9 | 0.861 | +2.9 | -5.7 |
| RR >= 2 to the nearest live opposing zone | 530 | 56.2 | 62.9 | -6.7 | 0.095 | -8.6 | -1.7 |
| no live opposing zone above / below | 41 | 58.5 | 58.3 | +0.3 | 1.000 | +4.2 | -9.3 |
| returned within 50 bars | 657 | 57.8 | 61.0 | -3.1 | 0.605 | -4.1 | -0.5 |
| returned after > 200 bars | 27 | 48.1 | 58.6 | -10.5 | 0.328 | -14.1 | -3.4 |
| formed in Asia (00-07 UTC) | 265 | 56.2 | 59.4 | -3.1 | 0.431 | -6.7 | +6.5 |
| formed in London (07-12 UTC) | 164 | 64.6 | 56.5 | +8.1 | 0.077 | +9.0 | +6.3 |
| formed in London/NY overlap (12-16 UTC) | 130 | 58.5 | 58.2 | +0.2 | 1.000 | +1.9 | -4.6 |
| BOS gate + FVG | 63 | 58.7 | 58.2 | +0.5 | 1.000 | -0.4 | +5.1 |
| BOS gate + FVG kept | 44 | 63.6 | 57.9 | +5.7 | 0.545 | +5.1 | +8.2 |
| BOS gate + with trend | 43 | 62.8 | 58.0 | +4.8 | 0.634 | +8.2 | -9.1 |
| BOS gate + discount/premium | 9 | 66.7 | 58.2 | +8.5 | 0.753 | -0.9 | +41.6 |
| BOS gate + sweep | 7 | 57.1 | 58.3 | -1.1 | 1.000 | -0.9 | n/a |
| BOS gate + FVG + with trend | 39 | 64.1 | 58.0 | +6.1 | 0.494 | +9.2 | -9.0 |
| BOS gate + FVG + discount/premium | 8 | 62.5 | 58.2 | +4.3 | 1.000 | -8.1 | +41.6 |
| BOS gate + departure >= 3 h | 59 | 57.6 | 58.3 | -0.7 | 1.000 | -3.0 | +8.3 |
| fractal BOS + FVG | 262 | 58.4 | 58.2 | +0.2 | 1.000 | +1.5 | -3.1 |
| FVG + departure >= 3 h | 334 | 56.9 | 59.3 | -2.5 | 0.512 | -0.9 | -6.4 |
| sweep + FVG | 96 | 60.4 | 58.0 | +2.5 | 0.655 | +4.4 | -4.2 |
| sweep + major BOS before return | 17 | 47.1 | 58.5 | -11.5 | 0.451 | -8.3 | -59.1 |
| with trend + discount/premium | 119 | 61.3 | 57.7 | +3.6 | 0.471 | -0.5 | +9.6 |
| NO major BOS (David: invalid) | 687 | 57.8 | 62.7 | -4.9 | 0.451 | -4.1 | -8.5 |

### Criteria — base AUDUSD M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 265 | 57.0 | 57.5 | -0.6 | 0.898 | +0.2 | -2.6 |
| major BOS before the return (any delay) | 417 | 58.3 | 57.4 | +0.9 | 0.746 | +0.4 | +2.6 |
| zone inside any major break's move | 429 | 58.3 | 57.4 | +0.9 | 0.758 | +0.5 | +2.4 |
| the break is a CHoCH | 89 | 64.0 | 57.3 | +6.8 | 0.236 | +7.8 | +4.2 |
| BOS gate (3-bar fractal swing) | 1237 | 55.7 | 58.8 | -3.1 | 0.099 | -2.8 | -3.7 |
| displacement >= 2 x avg body | 1959 | 56.5 | 59.5 | -3.1 | 0.116 | -1.8 | -5.8 |
| displacement >= 3 x avg body | 843 | 54.0 | 58.9 | -4.9 | 0.012 | -4.3 | -6.4 |
| FVG in the leg-out | 1932 | 59.1 | 54.4 | +4.7 | 0.015 | +4.3 | +5.7 |
| FVG >= 0.3 ATR | 1263 | 59.4 | 56.1 | +3.3 | 0.077 | +2.8 | +4.6 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 820 | 60.4 | 56.4 | +4.0 | 0.047 | +2.2 | +8.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2326 | 57.3 | 58.3 | -1.1 | 0.641 | +0.6 | -5.2 |
| base >= 3 candles | 619 | 58.3 | 57.3 | +1.1 | 0.650 | -0.6 | +5.2 |
| departure >= 3 zone heights before the return | 1689 | 57.0 | 58.1 | -1.1 | 0.582 | -1.3 | -0.7 |
| departure >= 2 ATR before the return | 1578 | 58.5 | 56.3 | +2.2 | 0.244 | +0.9 | +5.2 |
| leg-out candle range >= 2 zone heights | 1745 | 56.5 | 58.9 | -2.4 | 0.204 | -0.9 | -6.3 |
| zone height <= 0.5 ATR | 999 | 57.6 | 57.5 | +0.1 | 0.975 | +2.4 | -5.2 |
| zone height > 1 ATR | 497 | 56.1 | 57.8 | -1.6 | 0.522 | -2.5 | +0.4 |
| with the major trend | 1487 | 56.0 | 59.1 | -3.1 | 0.092 | -2.9 | -3.5 |
| against the major trend | 1457 | 59.0 | 56.0 | +3.0 | 0.100 | +2.8 | +3.5 |
| demand in discount / supply in premium (major range) | 1528 | 58.1 | 56.8 | +1.3 | 0.482 | +0.7 | +2.7 |
| ... of the last 100 bars' range | 1526 | 57.7 | 57.2 | +0.5 | 0.798 | +0.7 | +0.1 |
| liquidity sweep just before the leg-out | 629 | 55.3 | 58.1 | -2.7 | 0.224 | -4.4 | +1.7 |
| round-number level in / at the zone | 199 | 57.3 | 57.5 | -0.2 | 1.000 | -2.1 | +5.4 |
| RR >= 2 to the nearest live opposing zone | 2147 | 57.7 | 57.0 | +0.6 | 0.784 | +1.2 | -1.3 |
| no live opposing zone above / below | 91 | 57.1 | 57.5 | -0.4 | 1.000 | +0.1 | n/a |
| returned within 50 bars | 2537 | 57.0 | 60.5 | -3.5 | 0.187 | -2.6 | -6.2 |
| returned after > 200 bars | 158 | 53.2 | 57.7 | -4.6 | 0.281 | -5.0 | -2.3 |
| formed in Asia (00-07 UTC) | 938 | 55.1 | 58.6 | -3.5 | 0.080 | -3.5 | -3.5 |
| formed in London (07-12 UTC) | 633 | 60.0 | 56.8 | +3.2 | 0.141 | +2.0 | +6.3 |
| formed in London/NY overlap (12-16 UTC) | 538 | 56.3 | 57.7 | -1.4 | 0.550 | -3.2 | +3.9 |
| BOS gate + FVG | 218 | 56.0 | 57.6 | -1.6 | 0.667 | -0.0 | -6.1 |
| BOS gate + FVG kept | 147 | 56.5 | 57.5 | -1.1 | 0.794 | -0.9 | -1.3 |
| BOS gate + with trend | 176 | 53.4 | 57.7 | -4.3 | 0.273 | -3.6 | -6.4 |
| BOS gate + discount/premium | 30 | 50.0 | 57.6 | -7.6 | 0.454 | -13.2 | +21.7 |
| BOS gate + sweep | 39 | 41.0 | 57.7 | -16.7 | 0.051 | -14.9 | -25.3 |
| BOS gate + FVG + with trend | 144 | 50.7 | 57.8 | -7.1 | 0.102 | -5.5 | -11.7 |
| BOS gate + FVG + discount/premium | 25 | 52.0 | 57.5 | -5.5 | 0.685 | -9.6 | +16.6 |
| BOS gate + departure >= 3 h | 218 | 53.7 | 57.8 | -4.1 | 0.262 | -2.7 | -8.0 |
| fractal BOS + FVG | 943 | 56.9 | 57.7 | -0.8 | 0.679 | -1.2 | +0.2 |
| FVG + departure >= 3 h | 1289 | 59.0 | 56.3 | +2.8 | 0.143 | +2.2 | +4.0 |
| sweep + FVG | 426 | 56.1 | 57.7 | -1.6 | 0.559 | -3.0 | +2.9 |
| sweep + major BOS before return | 77 | 49.4 | 57.7 | -8.4 | 0.161 | -12.4 | +6.4 |
| with trend + discount/premium | 469 | 56.5 | 57.7 | -1.2 | 0.647 | -1.0 | -1.5 |
| NO major BOS (David: invalid) | 2680 | 57.5 | 57.0 | +0.6 | 0.896 | -0.2 | +2.6 |

### Criteria — base AUDUSD H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 103 | 58.3 | 63.0 | -4.8 | 0.388 | -0.9 | -15.8 |
| major BOS before the return (any delay) | 166 | 62.0 | 62.5 | -0.4 | 0.928 | +5.3 | -18.4 |
| zone inside any major break's move | 172 | 62.2 | 62.4 | -0.2 | 1.000 | +5.7 | -18.5 |
| the break is a CHoCH | 36 | 69.4 | 62.0 | +7.4 | 0.398 | +16.8 | -20.2 |
| BOS gate (3-bar fractal swing) | 339 | 64.0 | 61.0 | +3.0 | 0.413 | +3.9 | +0.6 |
| displacement >= 2 x avg body | 560 | 63.4 | 59.5 | +3.9 | 0.354 | +3.6 | +4.8 |
| displacement >= 3 x avg body | 263 | 63.5 | 61.8 | +1.7 | 0.707 | +1.7 | +1.4 |
| FVG in the leg-out | 505 | 62.6 | 62.0 | +0.6 | 0.868 | +3.7 | -7.9 |
| FVG >= 0.3 ATR | 326 | 62.6 | 62.2 | +0.4 | 0.938 | +2.2 | -4.5 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 217 | 59.9 | 63.4 | -3.4 | 0.409 | -1.3 | -9.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 595 | 62.0 | 63.6 | -1.6 | 0.728 | +1.5 | -10.4 |
| base >= 3 candles | 165 | 63.6 | 62.0 | +1.6 | 0.713 | -1.5 | +10.4 |
| departure >= 3 zone heights before the return | 422 | 58.8 | 66.9 | -8.1 | 0.026 | -7.0 | -10.6 |
| departure >= 2 ATR before the return | 400 | 59.2 | 65.8 | -6.6 | 0.068 | -5.4 | -9.8 |
| leg-out candle range >= 2 zone heights | 446 | 61.2 | 64.0 | -2.8 | 0.445 | -2.9 | -2.4 |
| zone height <= 0.5 ATR | 239 | 60.7 | 63.1 | -2.5 | 0.506 | -1.5 | -5.2 |
| zone height > 1 ATR | 156 | 64.1 | 61.9 | +2.2 | 0.634 | +0.0 | +7.4 |
| with the major trend | 381 | 62.5 | 62.3 | +0.2 | 1.000 | -1.3 | +4.0 |
| against the major trend | 379 | 62.3 | 62.5 | -0.2 | 1.000 | +1.3 | -4.0 |
| demand in discount / supply in premium (major range) | 383 | 64.5 | 60.2 | +4.3 | 0.231 | +8.2 | -6.1 |
| ... of the last 100 bars' range | 392 | 63.0 | 61.7 | +1.3 | 0.706 | +3.6 | -4.7 |
| liquidity sweep just before the leg-out | 149 | 60.4 | 62.8 | -2.4 | 0.638 | -2.5 | -2.0 |
| round-number level in / at the zone | 118 | 61.9 | 62.5 | -0.6 | 0.923 | -5.8 | +18.4 |
| RR >= 2 to the nearest live opposing zone | 510 | 61.8 | 63.6 | -1.8 | 0.633 | -0.6 | -6.3 |
| no live opposing zone above / below | 34 | 64.7 | 62.3 | +2.4 | 0.853 | +3.1 | n/a |
| returned within 50 bars | 644 | 62.7 | 60.3 | +2.4 | 0.679 | -1.8 | +15.8 |
| returned after > 200 bars | 64 | 57.8 | 62.8 | -5.0 | 0.490 | -2.0 | -14.8 |
| formed in Asia (00-07 UTC) | 286 | 62.9 | 62.0 | +0.9 | 0.818 | +1.0 | +0.9 |
| formed in London (07-12 UTC) | 180 | 60.6 | 62.9 | -2.4 | 0.598 | -6.7 | +8.0 |
| formed in London/NY overlap (12-16 UTC) | 154 | 59.7 | 63.0 | -3.3 | 0.464 | -0.7 | -10.1 |
| BOS gate + FVG | 88 | 58.0 | 62.9 | -5.0 | 0.414 | -0.3 | -17.9 |
| BOS gate + FVG kept | 54 | 55.6 | 62.9 | -7.3 | 0.307 | +2.5 | -32.8 |
| BOS gate + with trend | 67 | 52.2 | 63.3 | -11.1 | 0.084 | -10.8 | -11.8 |
| BOS gate + discount/premium | 8 | 75.0 | 62.2 | +12.8 | 0.505 | +38.5 | -14.1 |
| BOS gate + sweep | 7 | 57.1 | 62.4 | -5.3 | 1.000 | +4.9 | -14.1 |
| BOS gate + FVG + with trend | 58 | 53.4 | 63.1 | -9.7 | 0.160 | -6.5 | -18.5 |
| BOS gate + FVG + discount/premium | 5 | 80.0 | 62.3 | +17.7 | 0.662 | +38.3 | +2.9 |
| BOS gate + departure >= 3 h | 81 | 53.1 | 63.5 | -10.4 | 0.071 | -8.7 | -15.3 |
| fractal BOS + FVG | 261 | 63.6 | 61.7 | +1.9 | 0.632 | +4.5 | -4.9 |
| FVG + departure >= 3 h | 329 | 58.4 | 65.4 | -7.1 | 0.056 | -4.9 | -12.8 |
| sweep + FVG | 101 | 67.3 | 61.6 | +5.7 | 0.283 | +6.1 | +4.7 |
| sweep + major BOS before return | 28 | 67.9 | 62.2 | +5.7 | 0.551 | +10.0 | -6.9 |
| with trend + discount/premium | 106 | 66.0 | 61.8 | +4.3 | 0.461 | +6.2 | -1.5 |
| NO major BOS (David: invalid) | 657 | 63.0 | 58.3 | +4.8 | 0.380 | +0.9 | +15.8 |

### Criteria — base BITCOIN M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 225 | 57.3 | 56.5 | +0.8 | 0.832 | +3.4 | -4.5 |
| major BOS before the return (any delay) | 382 | 60.7 | 56.0 | +4.8 | 0.085 | +5.3 | +3.7 |
| zone inside any major break's move | 389 | 60.7 | 55.9 | +4.7 | 0.087 | +5.2 | +3.7 |
| the break is a CHoCH | 68 | 52.9 | 56.7 | -3.7 | 0.619 | -6.9 | +2.2 |
| BOS gate (3-bar fractal swing) | 1357 | 56.9 | 56.3 | +0.6 | 0.769 | +0.2 | +1.5 |
| displacement >= 2 x avg body | 1982 | 57.1 | 55.6 | +1.5 | 0.451 | +0.8 | +3.4 |
| displacement >= 3 x avg body | 895 | 55.5 | 57.0 | -1.5 | 0.463 | -1.6 | -1.2 |
| FVG in the leg-out | 1971 | 57.0 | 55.8 | +1.2 | 0.551 | +1.9 | -0.5 |
| FVG >= 0.3 ATR | 1262 | 57.2 | 56.1 | +1.1 | 0.533 | -1.3 | +7.4 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 829 | 59.2 | 55.5 | +3.7 | 0.075 | +3.8 | +3.4 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 2300 | 56.1 | 58.2 | -2.1 | 0.369 | -2.0 | -2.4 |
| base >= 3 candles | 627 | 58.2 | 56.1 | +2.1 | 0.357 | +2.0 | +2.4 |
| departure >= 3 zone heights before the return | 1686 | 57.2 | 55.8 | +1.4 | 0.455 | +2.0 | -0.1 |
| departure >= 2 ATR before the return | 1561 | 58.9 | 54.0 | +4.9 | 0.009 | +4.6 | +5.7 |
| leg-out candle range >= 2 zone heights | 1833 | 55.6 | 58.1 | -2.5 | 0.195 | -2.2 | -3.3 |
| zone height <= 0.5 ATR | 1037 | 54.2 | 57.9 | -3.7 | 0.057 | -2.7 | -6.3 |
| zone height > 1 ATR | 485 | 58.4 | 56.2 | +2.1 | 0.404 | +1.4 | +4.0 |
| with the major trend | 1468 | 56.4 | 56.8 | -0.3 | 0.863 | +1.4 | -4.9 |
| against the major trend | 1458 | 56.8 | 56.4 | +0.4 | 0.822 | -1.3 | +4.9 |
| demand in discount / supply in premium (major range) | 1472 | 57.0 | 56.2 | +0.8 | 0.661 | +0.5 | +1.6 |
| ... of the last 100 bars' range | 1486 | 56.4 | 56.8 | -0.4 | 0.857 | +0.1 | -1.6 |
| liquidity sweep just before the leg-out | 549 | 58.1 | 56.2 | +1.9 | 0.446 | +1.9 | +1.9 |
| round-number level in / at the zone | 451 | 59.9 | 56.0 | +3.9 | 0.134 | +3.6 | +4.6 |
| RR >= 2 to the nearest live opposing zone | 2191 | 56.2 | 57.6 | -1.4 | 0.524 | -3.2 | +3.8 |
| no live opposing zone above / below | 39 | 66.7 | 56.4 | +10.2 | 0.245 | +10.1 | n/a |
| returned within 50 bars | 2500 | 56.7 | 55.7 | +1.0 | 0.720 | +1.2 | +0.4 |
| returned after > 200 bars | 183 | 60.1 | 56.3 | +3.8 | 0.353 | +4.3 | +2.3 |
| formed in Asia (00-07 UTC) | 833 | 55.1 | 57.2 | -2.1 | 0.318 | -3.8 | +2.5 |
| formed in London (07-12 UTC) | 642 | 56.4 | 56.6 | -0.2 | 0.925 | -0.7 | +0.9 |
| formed in London/NY overlap (12-16 UTC) | 585 | 57.8 | 56.3 | +1.5 | 0.518 | +4.3 | -5.8 |
| BOS gate + FVG | 188 | 59.0 | 56.4 | +2.6 | 0.500 | +6.7 | -5.8 |
| BOS gate + FVG kept | 114 | 62.3 | 56.3 | +5.9 | 0.208 | +8.4 | +1.4 |
| BOS gate + with trend | 157 | 59.2 | 56.4 | +2.8 | 0.498 | +7.6 | -7.7 |
| BOS gate + discount/premium | 26 | 69.2 | 56.5 | +12.8 | 0.233 | +25.8 | -11.9 |
| BOS gate + sweep | 27 | 66.7 | 56.5 | +10.2 | 0.346 | +10.0 | +10.6 |
| BOS gate + FVG + with trend | 133 | 60.2 | 56.4 | +3.7 | 0.413 | +8.2 | -6.5 |
| BOS gate + FVG + discount/premium | 24 | 70.8 | 56.5 | +14.4 | 0.197 | +31.0 | -18.9 |
| BOS gate + departure >= 3 h | 196 | 57.1 | 56.5 | +0.6 | 0.885 | +3.2 | -4.3 |
| fractal BOS + FVG | 1020 | 57.1 | 56.3 | +0.7 | 0.722 | -0.1 | +2.9 |
| FVG + departure >= 3 h | 1324 | 57.5 | 55.8 | +1.6 | 0.380 | +2.1 | +0.4 |
| sweep + FVG | 397 | 58.7 | 56.2 | +2.4 | 0.385 | +0.8 | +6.2 |
| sweep + major BOS before return | 64 | 60.9 | 56.5 | +4.5 | 0.534 | +1.8 | +9.3 |
| with trend + discount/premium | 519 | 57.4 | 56.4 | +1.0 | 0.693 | +1.8 | -1.1 |
| NO major BOS (David: invalid) | 2702 | 56.5 | 57.3 | -0.8 | 0.837 | -3.4 | +4.5 |

### Criteria — base BITCOIN H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 37 | 73.0 | 56.0 | +17.0 | 0.056 | +15.9 | +24.0 |
| major BOS before the return (any delay) | 68 | 63.2 | 56.2 | +7.0 | 0.321 | +5.3 | +19.2 |
| zone inside any major break's move | 72 | 63.9 | 56.1 | +7.8 | 0.212 | +5.6 | +22.2 |
| the break is a CHoCH | 12 | 83.3 | 56.4 | +26.9 | 0.080 | +32.5 | +10.3 |
| BOS gate (3-bar fractal swing) | 390 | 56.4 | 57.3 | -0.9 | 0.831 | +1.7 | -7.1 |
| displacement >= 2 x avg body | 541 | 57.3 | 55.6 | +1.7 | 0.736 | +2.9 | -1.2 |
| displacement >= 3 x avg body | 285 | 55.8 | 57.5 | -1.7 | 0.644 | -3.2 | +1.6 |
| FVG in the leg-out | 478 | 56.7 | 57.1 | -0.4 | 0.935 | -1.8 | +2.6 |
| FVG >= 0.3 ATR | 305 | 56.1 | 57.4 | -1.3 | 0.758 | -0.7 | -2.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 251 | 53.8 | 58.4 | -4.7 | 0.242 | -6.7 | +0.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 559 | 57.4 | 55.1 | +2.4 | 0.597 | +3.2 | +0.6 |
| base >= 3 candles | 178 | 55.1 | 57.4 | -2.4 | 0.603 | -3.2 | -0.6 |
| departure >= 3 zone heights before the return | 427 | 54.6 | 60.0 | -5.4 | 0.154 | -1.7 | -13.9 |
| departure >= 2 ATR before the return | 417 | 55.9 | 58.1 | -2.2 | 0.539 | +1.4 | -10.8 |
| leg-out candle range >= 2 zone heights | 461 | 57.0 | 56.5 | +0.5 | 0.936 | -1.5 | +5.1 |
| zone height <= 0.5 ATR | 233 | 53.6 | 58.3 | -4.7 | 0.261 | -6.2 | -1.1 |
| zone height > 1 ATR | 148 | 55.4 | 57.2 | -1.8 | 0.716 | -3.4 | +1.2 |
| with the major trend | 365 | 57.0 | 56.7 | +0.3 | 1.000 | -0.9 | +3.1 |
| against the major trend | 371 | 56.6 | 57.1 | -0.5 | 0.943 | +0.6 | -3.1 |
| demand in discount / supply in premium (major range) | 372 | 56.5 | 57.3 | -0.8 | 0.887 | -0.8 | -0.7 |
| ... of the last 100 bars' range | 378 | 58.5 | 55.2 | +3.3 | 0.392 | +2.8 | +4.5 |
| liquidity sweep just before the leg-out | 145 | 58.6 | 56.4 | +2.2 | 0.636 | +5.0 | -3.2 |
| round-number level in / at the zone | 246 | 56.5 | 57.0 | -0.5 | 0.943 | +0.7 | -4.1 |
| RR >= 2 to the nearest live opposing zone | 520 | 53.1 | 65.9 | -12.8 | 0.001 | -12.6 | -13.4 |
| no live opposing zone above / below | 28 | 64.3 | 56.6 | +7.7 | 0.434 | +7.7 | n/a |
| returned within 50 bars | 618 | 55.7 | 63.0 | -7.4 | 0.152 | -8.9 | -3.4 |
| returned after > 200 bars | 42 | 59.5 | 56.7 | +2.8 | 0.751 | +4.4 | -6.7 |
| formed in Asia (00-07 UTC) | 180 | 52.2 | 58.3 | -6.1 | 0.168 | -2.4 | -13.5 |
| formed in London (07-12 UTC) | 181 | 57.5 | 56.7 | +0.8 | 0.867 | +0.0 | +2.5 |
| formed in London/NY overlap (12-16 UTC) | 179 | 58.1 | 56.5 | +1.6 | 0.723 | +1.8 | +1.2 |
| BOS gate + FVG | 31 | 67.7 | 56.4 | +11.4 | 0.259 | +10.2 | +18.8 |
| BOS gate + FVG kept | 24 | 70.8 | 56.4 | +14.5 | 0.203 | +13.5 | +18.8 |
| BOS gate + with trend | 25 | 68.0 | 56.5 | +11.5 | 0.302 | +8.6 | +43.9 |
| BOS gate + discount/premium | 2 | 100.0 | 56.7 | +43.3 | n/a | +43.2 | n/a |
| BOS gate + sweep | 2 | 100.0 | 56.7 | +43.3 | n/a | +43.2 | n/a |
| BOS gate + FVG + with trend | 21 | 61.9 | 56.7 | +5.2 | 0.659 | +0.9 | +43.9 |
| BOS gate + FVG + discount/premium | 2 | 100.0 | 56.7 | +43.3 | n/a | +43.2 | n/a |
| BOS gate + departure >= 3 h | 32 | 75.0 | 56.0 | +19.0 | 0.045 | +18.0 | +24.0 |
| fractal BOS + FVG | 285 | 55.1 | 58.0 | -2.9 | 0.438 | -1.3 | -6.3 |
| FVG + departure >= 3 h | 339 | 54.0 | 59.3 | -5.3 | 0.162 | -5.1 | -5.9 |
| sweep + FVG | 98 | 55.1 | 57.1 | -2.0 | 0.730 | +2.0 | -9.4 |
| sweep + major BOS before return | 10 | 70.0 | 56.7 | +13.3 | 0.526 | +9.8 | +43.7 |
| with trend + discount/premium | 170 | 54.1 | 57.7 | -3.6 | 0.428 | -3.3 | -4.0 |
| NO major BOS (David: invalid) | 700 | 56.0 | 73.0 | -17.0 | 0.057 | -15.9 | -24.0 |
