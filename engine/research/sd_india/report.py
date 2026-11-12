"""engine_data/india/results.json -> one self-contained HTML results page (path = argv[1])."""
import json, os, sys, statistics as st
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import backtest as B

IST = timezone(timedelta(hours=5, minutes=30))
res = json.load(open(os.path.join(B.DATA, "results.json")))
ind = [r for r in res if r["group"] == "india"]
fx = [r for r in res if r["group"] == "fx"]
d = lambda ms: datetime.fromtimestamp(ms / 1000, IST)


def trades(rows, run="hold"):
    return sorted([t for r in rows for t in r["runs"].get(run, [])], key=lambda t: t["t_exit"])


def tstat(tr):
    rs = [t["R"] for t in tr]
    s = st.pstdev(rs)
    return st.mean(rs) / (s / len(rs) ** .5) if s else 0


def fmt(x, p=2, sign=True):
    return ("−" if x < 0 else ("+" if sign and x > 0 else "")) + f"{abs(x):.{p}f}"


def curve(tr, w=520, h=170, label=""):
    eq, pts = 0.0, [0.0]
    for t in tr:
        eq += t["R"]; pts.append(eq)
    lo, hi = min(pts + [0]), max(pts + [0])
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    L, R, T, Bm = 44, 12, 12, 26
    X = lambda i: L + (w - L - R) * i / max(1, len(pts) - 1)
    Y = lambda v: T + (h - T - Bm) * (hi - v) / (hi - lo)
    step = next(s for s in (1, 2, 5, 10, 20, 25, 50, 100) if (hi - lo) / s <= 6)
    g = []
    v = (int(lo / step) - 1) * step
    while v <= hi:
        if v >= lo:
            g.append(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"zero" if v == 0 else "grid"}"/>'
                     f'<text x="{L-6}" y="{Y(v)+4:.1f}" class="tick" text-anchor="end">{fmt(v,0) if v else "0"}</text>')
        v += step
    path = " ".join(f'{"M" if i == 0 else "L"}{X(i):.1f},{Y(p):.1f}' for i, p in enumerate(pts))
    area = path + f" L{X(len(pts)-1):.1f},{Y(max(lo,0) if lo>0 else 0):.1f} L{X(0):.1f},{Y(0):.1f} Z"
    d0, d1 = d(tr[0]["t_exit"]).strftime("%b %Y"), d(tr[-1]["t_exit"]).strftime("%b %Y")
    hits = "".join(f'<circle cx="{X(i+1):.1f}" cy="{Y(pts[i+1]):.1f}" r="5" class="hit"><title>{d(t["t_exit"]).strftime("%d %b %Y")} · {t["side"]} · {fmt(t["R"])} R · total {fmt(pts[i+1],1)} R</title></circle>'
                   for i, t in enumerate(tr))
    end = f'<circle cx="{X(len(pts)-1):.1f}" cy="{Y(pts[-1]):.1f}" r="4" class="end"/>'
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}: cumulative R">{"".join(g)}'
            f'<path d="{area}" class="area"/><path d="{path}" class="line"/>{end}{hits}'
            f'<text x="{L}" y="{h-6}" class="tick">{d0}</text><text x="{w-R}" y="{h-6}" class="tick" text-anchor="end">{d1}</text>'
            f'<text x="{w-R}" y="{Y(pts[-1])-9:.1f}" class="endlab" text-anchor="end">{fmt(pts[-1],1)} R</text></svg>')


def years(tr, w=620, h=200):
    by = {}
    for t in tr:
        by.setdefault(d(t["t_exit"]).year, []).append(t["R"])
    ys = sorted(by); vals = [sum(by[y]) for y in ys]
    m = max(abs(v) for v in vals) * 1.15
    L, R, T, Bm = 40, 8, 14, 24
    bw = (w - L - R) / len(ys)
    Y = lambda v: T + (h - T - Bm) * (m - v) / (2 * m)
    out = [f'<line x1="{L}" x2="{w-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="zero"/>']
    for v in (-m / 1.15, m / 1.15):
        out.append(f'<text x="{L-6}" y="{Y(v)+4:.1f}" class="tick" text-anchor="end">{fmt(v,0)}</text>'
                   f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>')
    for i, (y, v) in enumerate(zip(ys, vals)):
        x = L + i * bw + 2
        y0, y1 = sorted((Y(0), Y(v)))
        out.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw-4:.1f}" height="{max(1,y1-y0):.1f}" rx="2" class="{"pos" if v>=0 else "neg"}">'
                   f'<title>{y}: {len(by[y])} trades, {fmt(v,1)} R</title></rect>')
        if i % 2 == 0 or len(ys) < 10:
            out.append(f'<text x="{x+(bw-4)/2:.1f}" y="{h-6}" class="tick" text-anchor="middle">{str(y)[2:] if len(ys)>10 else y}</text>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Daily: R per year">{"".join(out)}</svg>'


def row(name, tr, kind=""):
    s = B.stats(tr)
    if not s["n"]:
        return f"<tr><td>{name}</td><td colspan=6 class=muted>no trades</td></tr>"
    cls = "pos" if s["avgR"] > 0 else "neg"
    return (f'<tr><td>{name}<span class="kind">{kind}</span></td><td>{s["n"]}</td><td>{s["win"]:.0f}%</td><td>{s["avg_rr"]:.1f}</td>'
            f'<td class="{cls}">{fmt(s["avgR"])}</td><td class="{cls}">{fmt(s["totR"],1)}</td><td>{s["pf"] if s["pf"] is not None else "–"}</td></tr>')


PANELS = [("D1", "Daily", "Jan 2010 → Nov 2026, 14 markets"), ("H1", "1 hour", "Nov 2023 → Nov 2026, 14 markets"),
          ("M15", "15 min (the live timeframe)", "Aug → Nov 2026 (Yahoo keeps 60 days)")]
tiles, charts = [], []
for tf, nm, span in PANELS:
    tr = trades([r for r in ind if r["tf"] == tf]); s = B.stats(tr)
    tiles.append((nm, s, tstat(tr), span))
    charts.append(f'<figure><figcaption><b>{nm}</b><span>{span} · {s["n"]} trades · {fmt(s["avgR"])} R a trade</span></figcaption>{curve(tr, label=nm)}</figure>')
ftr = trades(fx); fs = B.stats(ftr)
tiles.append(("Forex + gold, M15 (reference)", fs, tstat(ftr), "Jan → Nov 2026, GOLD EURUSD GBPUSD USDJPY"))
charts.append(f'<figure><figcaption><b>Reference: forex + gold, M15</b><span>same simulator, FxPro spread · {fs["n"]} trades · {fmt(fs["avgR"])} R a trade</span></figcaption>{curve(ftr, label="FX")}</figure>')

h1 = trades([r for r in ind if r["tf"] == "H1"])
h1r = sorted((t["R"] for t in h1), reverse=True)
d1 = trades([r for r in ind if r["tf"] == "D1"])

tables = []
for tf, nm, _ in PANELS:
    rows = [r for r in ind if r["tf"] == tf]
    body = "".join(row(r["name"], r["runs"]["hold"], " index" if r["name"] in B.INDICES else "") for r in rows)
    body += row("<b>All 14</b>", trades(rows))
    tables.append(f'<details{" open" if tf=="D1" else ""}><summary>{nm}</summary><div class="tw"><table><thead><tr><th>Market</th><th>Trades</th><th>Won</th><th>Avg R:R</th><th>R / trade</th><th>Total R</th><th>PF</th></tr></thead><tbody>{body}</tbody></table></div></details>')

eod = []
for tf in ("M15", "H1"):
    for grp, f in (("indices", lambda r: r["name"] in B.INDICES), ("stocks", lambda r: r["name"] not in B.INDICES)):
        rows = [r for r in ind if r["tf"] == tf and f(r)]
        a, b = B.stats(trades(rows)), B.stats(trades(rows, "eod"))
        eod.append(f'<tr><td>{tf} {grp}</td><td>{a["n"]}</td><td class="{"pos" if a["avgR"]>0 else "neg"}">{fmt(a["avgR"])}</td><td class="{"pos" if b["avgR"]>0 else "neg"}">{fmt(b["avgR"])}</td></tr>')

tile_html = "".join(
    f'<div class="tile"><div class="tl">{nm}</div><div class="tv {"pos" if s["avgR"]>0 else "neg"}">{fmt(s["avgR"])} <small>R / trade</small></div>'
    f'<div class="ts">{s["n"]} trades · {s["win"]:.0f}% won · total {fmt(s["totR"],1)} R · t = {fmt(t,1)}</div></div>'
    for nm, s, t, span in tiles)

html = f'''<title>S&amp;D David on NSE</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Space+Grotesk:wght@500;600&display=swap">
<style>
/* layout: one reading column — verdict, tiles, four small-multiple curves, year bars, tables, method */
:root {{ --bg:#fbfbf9; --surface:#ffffff; --fg:#141413; --muted:#5d5c57; --line:#e3e2dc; --accent:#2a78d6; --accent-soft:rgba(42,120,214,.10);
  --pos:#1d6fd0; --neg:#c4521f; --zero:#a9a8a0;
  --display:"Space Grotesk",system-ui,sans-serif; --body:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141413; --surface:#1c1c1a; --fg:#efeee9; --muted:#b4b3aa; --line:#33332f; --accent:#3987e5; --accent-soft:rgba(57,135,229,.16); --pos:#5598e7; --neg:#e07a4c; --zero:#6b6a64; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#141413; --surface:#1c1c1a; --fg:#efeee9; --muted:#b4b3aa; --line:#33332f; --accent:#3987e5; --accent-soft:rgba(57,135,229,.16); --pos:#5598e7; --neg:#e07a4c; --zero:#6b6a64; color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.55 var(--body); }}
main {{ max-width:1040px; margin:0 auto; padding-block:28px 56px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); display:grid; gap:30px; }}
h1,h2 {{ font-family:var(--display); text-wrap:balance; margin:0; letter-spacing:-.01em }}
h1 {{ font-size:clamp(26px,4vw,36px); line-height:1.15 }} h2 {{ font-size:20px }}
p {{ margin:0; max-width:68ch }} .muted {{ color:var(--muted) }}
.eyebrow {{ font:500 12px var(--mono); text-transform:uppercase; letter-spacing:.08em; color:var(--muted) }}
.head {{ display:grid; gap:10px }}
.verdict {{ border-left:3px solid var(--neg); padding:4px 0 4px 14px; display:grid; gap:6px }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px }}
.tile {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:14px 16px; display:grid; gap:4px }}
.tl {{ font-size:13px; color:var(--muted) }} .tv {{ font:600 28px var(--display); font-variant-numeric:tabular-nums }} .tv small {{ font:400 13px var(--body); color:var(--muted) }}
.ts {{ font:12px var(--mono); color:var(--muted); font-variant-numeric:tabular-nums }}
.pos {{ color:var(--pos) }} .neg {{ color:var(--neg) }}
.grid2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr)); gap:18px }}
figure {{ margin:0; display:grid; gap:6px; min-width:0 }} figcaption {{ display:grid; font-size:14px }} figcaption span {{ color:var(--muted); font-size:12.5px }}
svg {{ width:100%; height:auto; display:block; overflow:visible }}
svg .grid {{ stroke:var(--line); stroke-width:1 }} svg .zero {{ stroke:var(--zero); stroke-width:1 }}
svg .tick {{ fill:var(--muted); font:11px var(--mono) }} svg .endlab {{ fill:var(--fg); font:500 12px var(--mono) }}
svg .line {{ fill:none; stroke:var(--accent); stroke-width:2; stroke-linejoin:round }} svg .area {{ fill:var(--accent-soft); stroke:none }}
svg .end {{ fill:var(--accent); stroke:var(--surface); stroke-width:2 }} svg .hit {{ fill:transparent; stroke:none; cursor:default }} svg .hit:hover {{ fill:var(--accent) }}
svg rect.pos {{ fill:var(--pos) }} svg rect.neg {{ fill:var(--neg) }}
section {{ display:grid; gap:12px }}
.tw {{ overflow-x:auto }} table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; font-size:14px }}
th,td {{ padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); white-space:nowrap }} th:first-child,td:first-child {{ text-align:left }}
th {{ font:500 12px var(--mono); color:var(--muted); text-transform:uppercase; letter-spacing:.05em }}
.kind {{ font:11px var(--mono); color:var(--muted); margin-left:6px }}
details {{ border:1px solid var(--line); border-radius:8px; background:var(--surface); padding:4px 14px }} details[open] {{ padding-bottom:10px }}
summary {{ cursor:pointer; padding:8px 0; font-weight:600 }} summary:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px }}
ul {{ margin:0; padding-left:20px; display:grid; gap:6px; max-width:72ch }}
code {{ font:13px var(--mono) }}
</style>
<main>
<div class="head"><div class="eyebrow">Backtest · 12 Nov 2026 · NSE / BSE</div>
<h1>Does S&amp;D David work on the Indian market?</h1>
<div class="verdict"><p><b>No edge, as it trades today.</b> On 15+ years of daily candles it loses {abs(tiles[0][1]["avgR"]):.2f} R a trade after costs (−0.08 R even with zero costs). On 1-hour candles it shows {fmt(tiles[1][1]["avgR"])} R, but that comes from 5 outlier trades (+{h1r[4]:.1f} to +{h1r[0]:.1f} R); without them it is {fmt(sum(h1r[5:]),1)} R. The 15-minute test covers only 60 days ({tiles[2][1]["n"]} trades). The same simulator on forex and gold gives {fmt(fs["avgR"])} R, so the Indian result is in line with the other markets.</p></div></div>
<div class="tiles">{tile_html}</div>
<p class="muted">R = profit as a multiple of the stop distance, after costs. t = how many standard errors the average is from zero; under 2 means it could be luck.</p>
<section><h2>Running total of R, trade by trade</h2><div class="grid2">{"".join(charts)}</div></section>
<section><h2>Daily candles: R per year</h2><p class="muted">17 years, both signs: no year-after-year pattern. 2020 (the COVID fall) lost 18.9 R on 15 trades.</p>{years(d1)}</section>
<section><h2>Each market</h2>{"".join(tables)}</section>
<section><h2>Intraday square-off at 15:30</h2><p class="muted">Indian intraday (MIS) positions are closed at the end of the day. The same trades with that rule: it helps the indices and hurts the stocks. The signs flip between groups, which is what noise looks like.</p>
<div class="tw"><table><thead><tr><th>Set</th><th>Trades</th><th>Hold to SL / TP</th><th>Close at day end</th></tr></thead><tbody>{"".join(eod)}</tbody></table></div></section>
<section><h2>What was tested</h2><ul>
<li>The live rule unchanged: <code>sd_david.zones()</code> + the <code>sdd_book.py</code> order. Every valid, fresh zone gets a limit at candle A's wick, a stop 10 ticks beyond A, and a target at T1 (Fib 0.618). The target follows T1 while waiting, and the order is cancelled when the zone ends.</li>
<li>Walk-forward with no look-ahead: after every closed candle the zones are found again on the last 3,000 candles that had closed by then, as the engine does live.</li>
<li>Markets: NIFTY 50, BANK NIFTY, FIN NIFTY, SENSEX, RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS, SBIN, AXISBANK, LT, ITC, BHARTIARTL. Candles from Yahoo Finance (index cash charts, not futures).</li>
<li>Costs per round trip: index futures 0.03 %, stocks 0.06 % (STT, exchange, stamp, GST, brokerage, a tick of slippage). A zone whose cost is over 25 % of its stop is skipped, as live.</li>
<li>Fills: the fill candle can stop a trade but cannot take its profit. A candle that touches both stop and target counts as the stop. A gap through the stop exits at the open.</li>
</ul></section>
<section><h2>Limits of this test</h2><ul>
<li>15-minute candles, the live timeframe, are only available for the last 60 days. A real 15-minute test needs a paid NSE intraday history.</li>
<li>Index charts are spot. Futures trade at a premium, and rollover days are not modelled.</li>
<li>Few zones: about one trade per market per month on 1-hour candles. A small sample makes every per-market figure shaky; read the "All 14" rows.</li>
</ul></section>
</main>'''
open(sys.argv[1], "w").write(html)
print("ok", len(html))
