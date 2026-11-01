# Supply & demand — the research behind `engine/supply_demand.py` (2026-10-30)

David asked for supply / demand on `/smc`, **only the valid zones**, researched "from the internet and all open
source". Three Fable 5.1 agents worked on it overnight (read-only, no MT5): the method, the open-source tools, and
a measurement of whether any validity rule actually works. `brief.md` is the brief all three were given.

The result lives in `engine/supply_demand.py`; this folder is the evidence. Everything here re-runs offline from
`engine_data/history/` — no MT5, no network.

| file | what it is | re-run |
|---|---|---|
| `brief.md` | the task all three agents were given, with David's own rules quoted | — |
| `method_report.md` | what supply & demand IS across 26 sources, every rule with its sources, the disagreements and what was chosen, and the spec the engine module implements | — |
| `sd_proto.py` | the prototype the spec was written against (same algorithm as `engine/supply_demand.py`) | `python3 sd_proto.py > run_output.txt` (~10 s) |
| `run_output.txt` | its output on GOLD / EURUSD M15 + H1: counts, kinds, what was filtered and why, the newest valid zones | |
| `verify.py` | 19 checks: two published worked examples reproduced (therighttrader, Dukascopy), David's no-BOS case, and internal checks on real bars incl. a **no-look-ahead** test | `python3 verify.py > verify_output.txt` (~5 s) |
| `verify_output.txt` | their output — ALL OK | |
| `opensource_report.md` | the six public tools read line by line (Shved MQL5, cmike444, Svopex, Flux Charts, BigBeluga, SDZ PRO), each algorithm written out exactly, what is worth copying | — |
| `ports.py` | faithful numpy ports of those six (ambiguities marked `AMBIGUOUS:`) | imported by the two below |
| `toy_tests.py` | 31 behaviour checks of the ports against the originals' documented behaviour (box geometry, what counts as a touch, what kills a zone) | `python3 toy_tests.py > toy_tests_output.txt` (~5 s) |
| `toy_tests_output.txt`, `verify_output.txt`, `run_output.txt`, `compare_output.txt`, `proto_vs_engine_output.txt` | the saved output of each script above, regenerated 2026-10-30 09:30 | |
| `compare.py` | the six tools + David's gate on our bars: how many zones each draws, how much they agree, how often a tool has a zone at a major break | `python3 compare.py > compare_output.txt` (~3 min, also writes `compare_results.json`) |
| `proto_vs_engine.py` | proves the shipped `engine/supply_demand.py` finds exactly what the prototype the spec was written against finds (boxes, kinds, life cycle, score, every filtered reason), on GOLD + EURUSD M15 + H1 | `python3 proto_vs_engine.py > proto_vs_engine_output.txt` (~30 s) |
| `sources.md` | the literature review with URLs and a credibility grade per claim | — |
| `validity_report.md` | the measurement: do the "valid" zones hold better than matched random levels? | — |
| `sd_test.py` | that test | `python3 sd_test.py --out <dir> --procs 6` (~10 min, writes `tables.md`, `scan.txt`, `zones.json`) |
| `tables.md`, `scan.txt` | its tables and the 45-criteria × 24-cell consistency scan | |

Run them from this folder with plain `python3` (not `-I`: the scripts import each other).

## What the research concluded

1. **The method** (`method_report.md` §3): a base of 1–3 small-body candles (or David's last opposite candle)
   before a displacement candle, box = the base's wicks with the body edge as the entry line, kind RBR / DBD /
   RBD / DBR, life cycle fresh → tested → spent → broken → flipped. Where the sources disagreed, David's V5 rules
   won; §4 lists each disagreement and the choice.
2. **The gate** is David's, and no public tool has it: the move out of the box must close beyond a confirmed swing
   (a major BOS / CHoCH), and price must not come back to the box before that break. It removes ~90 % of
   displacement candidates — 6 zones a day on GOLD M15 become under one.
3. **It does not make the zones better.** 39,106 zones over 16 months held at the first return 58.2 % of the time;
   139,632 matched random levels of the same size, side and distance held 57.9 %. The BOS gate, freshness, the
   FVG, base count, displacement, trend, premium / discount, sweeps, sessions and round numbers all move that by
   ±2 points with no consistent sign (`scan.txt`). So **valid = David's definition, still intact** — a structure
   filter that keeps the chart to the zones his strategy trades from — never "more likely to hold". The page says
   this in the side panel, and the 0–10 checklist is displayed, never used as a filter.

## Not kept

- `dl/` — the downloaded originals (the .mq4 / .mq5 files, the Pine sources from
  `pine-facade.tradingview.com/pine-facade/get/<PUB;id>/last`, cmike444's JS, the text of Seiden's 2005 SFO
  article). They were scratch; every URL is in `opensource_report.md` §1 and `sources.md`.
- `zones.json` (~120 MB, every zone / control / shuffled zone of the validity test) — regenerate with `sd_test.py`
  when needed; `tables.md` and `scan.txt` hold everything the report cites.

The outputs in this folder were regenerated on 2026-10-30 09:30 on newer bars than the overnight run, so the
counts differ a little from the numbers quoted in the reports (the bar files keep growing); the behaviour checks,
the worked examples and the conclusions are unchanged.
