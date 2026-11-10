"""Build one HTML page with every Kronos forecast drawn on the real candles that followed.
Sources: backtest GOLD (342) + live signals.jsonl (26-28 Oct, 20 symbols). Bars: engine_data/history/<SYM>.json M15."""
import gzip, json, bisect, sys, datetime as D

ROOT = "/home/david/forex/engine_data"
OUT = sys.argv[1]
BEFORE, AFTER = 40, 12

def load(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        return [json.loads(l) for l in f if l.strip()]

fc = [dict(d, src="backtest") for d in load(f"{ROOT}/backtest/kronos_claude_bos_zone/data/kronos_GOLD.jsonl.gz")]
fc += [dict(d, src="live") for d in load(f"{ROOT}/kronos/signals.jsonl")]

bars, digits = {}, {}
def get(sym):
    if sym not in bars:
        h = json.load(open(f"{ROOT}/history/{sym}.json"))
        m = h["bars"]["M15"]
        bars[sym] = ([b[0] for b in m], m)
        digits[sym] = h.get("info", {}).get("digits", 5)
    return bars[sym]

out, skipped, mism = [], 0, 0
for d in fc:
    sym = d["symbol"]
    ts, m = get(sym)
    i = bisect.bisect_left(ts, d["bar_t"])
    if i >= len(ts) or ts[i] != d["bar_t"]:
        skipped += 1
        continue
    if abs(m[i][4] - d["last"]) > 10 ** -digits[sym] * 50:
        mism += 1
    nd = digits[sym]
    r = lambda x: round(x, nd)
    seg = m[max(0, i - BEFORE + 1): i + 1 + AFTER]
    n_after = len(m[i + 1: i + 1 + AFTER])
    h = d["horizon"]
    real = m[i + h][4] if i + h < len(m) else None
    out.append({
        "s": d["src"], "y": sym, "t": d["bar_t"], "l": d["last"], "p": d["p_up"], "n": d.get("paths"),
        "md": [r(x) for x in d["median"]], "lo": [r(x) for x in d["q10"]], "hi": [r(x) for x in d["q90"]],
        "b": [[r(b[1]), r(b[2]), r(b[3]), r(b[4])] for b in seg], "bt": [b[0] for b in seg],
        "k": len(seg) - n_after - 1,  # index of the forecast bar inside b
        "rl": real, "dg": nd,
    })

out.sort(key=lambda x: (x["s"] != "live", x["t"], x["y"]))
print(f"{len(out)} forecasts, {skipped} skipped (no bar), {mism} last-price mismatch", file=sys.stderr)

html = open(sys.argv[2]).read().replace("/*DATA*/null", json.dumps(out, separators=(",", ":")))
html = html.replace("__BUILT__", D.datetime.now().strftime("%Y-%m-%d %H:%M"))
open(OUT, "w").write(html)
