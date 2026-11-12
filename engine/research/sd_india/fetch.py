"""Indian market candles from Yahoo's public chart API → engine_data/india/<NAME>_<TF>.json ([t_ms, o, h, l, c, v] rows).
15m: last 60 days (Yahoo's limit) · 1h: last 730 days · 1d: since 2010."""
import json, os, sys, time, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "engine_data", "india")
SYMBOLS = {  # name -> Yahoo ticker
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY_FIN_SERVICE.NS", "SENSEX": "^BSESN",
    "RELIANCE": "RELIANCE.NS", "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS", "INFY": "INFY.NS",
    "TCS": "TCS.NS", "SBIN": "SBIN.NS", "AXISBANK": "AXISBANK.NS", "LT": "LT.NS", "ITC": "ITC.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
}
TFS = {"M15": ("15m", "range=60d"), "H1": ("60m", "range=730d"), "D1": ("1d", "period1=1262304000&period2=%d")}


def get(tk, interval, rng):
    if "%d" in rng:
        rng = rng % int(time.time())
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(tk)}?interval={interval}&{rng}"
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
    r = d["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(r.get("timestamp") or []):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c) or h < l:
            continue
        rows.append([t * 1000, o, h, l, c, q["volume"][i] or 0])
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, tk in SYMBOLS.items():
        for tf, (iv, rng) in TFS.items():
            rows = get(tk, iv, rng)
            with open(os.path.join(OUT, f"{name}_{tf}.json"), "w") as f:
                json.dump({"symbol": name, "ticker": tk, "tf": tf, "fetched": int(time.time()), "bars": rows}, f)
            print(name, tf, len(rows), time.strftime("%Y-%m-%d", time.gmtime(rows[0][0] / 1000)) if rows else "-")
            time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
