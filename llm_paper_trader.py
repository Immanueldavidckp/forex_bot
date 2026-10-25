#!/usr/bin/env python3
"""
llm_paper_trader.py - market plumbing for the forex desk: settings (desk.env), pair maths, trading hours,
candles (OANDA, the MT5 terminal, or Yahoo Finance with no key), indicators, and a fake feed for plumbing tests.

  python3 llm_paper_trader.py                 # EUR/USD 1h: latest candles, indicators, session
  python3 llm_paper_trader.py USD/JPY 4h
"""
import json, os, random, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    NY = ZoneInfo("America/New_York")
except Exception:                                   # no tz database: New York winter time
    NY = timezone(timedelta(hours=-5))

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = {
    "LIVE": "0", "OANDA_ENV": "practice", "OANDA_TOKEN": "", "OANDA_ACCOUNT": "", "DATA_SOURCE": "auto",
    "BROKER": "oanda", "MT5_MAGIC": "21102026", "MT5_ALLOW_REAL": "0",
    "RISK_PER_TRADE_PCT": "1.0", "MAX_LEVERAGE": "10", "MAX_NOTIONAL_USD": "1000", "DAILY_LOSS_LIMIT_PCT": "3",
    "MIN_CONFIDENCE": "0.6", "MIN_REWARD_RISK": "1.5", "EVENT_BLACKOUT_HOURS": "2", "MAX_SLIPPAGE_PIPS": "3",
    "SPREAD_PIPS": "", "OPENCLAW_CMD": "openclaw agent --agent main --json --timeout 300", "OPENCLAW_TIMEOUT": "360",
}


def load_env(path=os.path.join(HERE, "desk.env")):
    """desk.env (KEY=VALUE, # comments) over the defaults; real environment variables win over both."""
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        for line in open(path):
            k, eq, v = line.partition("=")
            if eq and not k.strip().startswith("#"):
                cfg[k.strip()] = v.split(" #")[0].strip().strip("'\"")
    cfg.update({k: os.environ[k] for k in cfg if k in os.environ})
    return cfg


CFG = load_env()
INTERVAL_SEC = {"15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
OANDA_GRANULARITY = {"15m": "M15", "30m": "M30", "1h": "H1", "4h": "H4", "1d": "D"}
YAHOO_RANGE = {"15m": ("15m", "10d"), "30m": ("30m", "20d"), "1h": ("1h", "30d"), "4h": ("1h", "120d"),
               "1d": ("1d", "2y")}
TYPICAL_SPREAD_PIPS = {"EUR/USD": 1.0, "USD/JPY": 1.1, "GBP/USD": 1.4, "AUD/USD": 1.3, "USD/CHF": 1.6,
                       "USD/CAD": 1.7, "NZD/USD": 1.8}
MOCK_START = {"EUR/USD": 1.085, "USD/JPY": 150.0, "GBP/USD": 1.27, "AUD/USD": 0.66, "USD/CHF": 0.88,
              "USD/CAD": 1.37, "NZD/USD": 0.60}


# ---------------------------------------------------------------- pair maths (account currency is USD)
def norm(symbol):
    """'eurusd', 'EUR_USD', 'EUR/USD' -> 'EUR/USD'. USD must be one side so P&L converts without a third rate."""
    s = symbol.upper().replace("_", "/").replace("-", "/")
    if "/" not in s and len(s) == 6:
        s = s[:3] + "/" + s[3:]
    base, _, quote = s.partition("/")
    if len(base) != 3 or len(quote) != 3 or base == quote or "USD" not in (base, quote):
        raise ValueError(f"{symbol}: use a USD pair such as EUR/USD, GBP/USD, AUD/USD, USD/JPY, USD/CAD")
    return f"{base}/{quote}"


def instrument(symbol):
    return norm(symbol).replace("/", "_")


def pip_size(symbol):
    return 0.01 if norm(symbol).endswith("JPY") else 0.0001


def decimals(symbol):
    return 3 if norm(symbol).endswith("JPY") else 5


def spread_pips(symbol):
    return float(CFG["SPREAD_PIPS"] or TYPICAL_SPREAD_PIPS.get(norm(symbol), 2.0))


def usd_per_unit(symbol, price):
    """USD gained or lost per unit of the base currency when the price moves by 1.0."""
    return 1.0 if norm(symbol).endswith("/USD") else 1.0 / price


def notional_usd(symbol, units, price):
    return units * price if norm(symbol).endswith("/USD") else float(units)


def pnl_usd(symbol, side, units, entry, exit_price):
    move = (exit_price - entry) * (1 if side == "long" else -1)
    return units * move * usd_per_unit(symbol, exit_price)


# ---------------------------------------------------------------- trading hours
def _ny(t=None):
    return (t or datetime.now(timezone.utc)).astimezone(NY)


def market_open(t=None):
    """Spot FX trades from Sunday 17:00 to Friday 17:00 New York time."""
    ny = _ny(t)
    wd, h = ny.weekday(), ny.hour
    return not (wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 17))


def hours_to_close(t=None):
    """Hours until the weekly close, Friday 17:00 New York."""
    ny = _ny(t)
    close = (ny + timedelta(days=(4 - ny.weekday()) % 7)).replace(hour=17, minute=0, second=0, microsecond=0)
    if close <= ny:
        close += timedelta(days=7)
    return (close.astimezone(timezone.utc) - ny.astimezone(timezone.utc)).total_seconds() / 3600


def in_rollover(t=None):
    """16:45-17:15 New York: daily rollover, spreads blow out and liquidity is thin."""
    ny = _ny(t)
    return 16 * 60 + 45 <= ny.hour * 60 + ny.minute < 17 * 60 + 15


def sessions(t=None):
    """Main FX sessions open now (approximate UTC hours, ignoring daylight saving)."""
    h = (t or datetime.now(timezone.utc)).astimezone(timezone.utc).hour
    hours = {"sydney": (21, 6), "tokyo": (0, 9), "london": (7, 16), "new_york": (12, 21)}
    return [s for s, (a, b) in hours.items() if (a <= h < b if a < b else h >= a or h < b)]


def trading_day(t=None):
    """The FX trading day rolls over at 17:00 New York."""
    return (_ny(t) + timedelta(hours=7)).strftime("%Y-%m-%d")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------- data
def http_json(url, headers=None, body=None, method=None, timeout=20):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", **(headers or {})},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}: "
                           f"{e.read().decode(errors='replace')[:300]}") from None


def oanda(path, body=None, method=None):
    """OANDA v20 REST call. OANDA_ENV=practice -> demo server, live -> real-money server."""
    if not CFG["OANDA_TOKEN"]:
        raise RuntimeError("OANDA_TOKEN is not set in desk.env")
    host = "api-fxtrade.oanda.com" if CFG["OANDA_ENV"] == "live" else "api-fxpractice.oanda.com"
    return http_json(f"https://{host}{path}", {"Authorization": f"Bearer {CFG['OANDA_TOKEN']}",
                                               "Content-Type": "application/json",
                                               "Accept-Datetime-Format": "UNIX"}, body, method)


def _source():
    if CFG["DATA_SOURCE"] != "auto":
        return CFG["DATA_SOURCE"]
    return "mt5" if CFG["BROKER"] == "mt5" else ("oanda" if CFG["OANDA_TOKEN"] else "yahoo")


MT5_TF = {"15m": "M15", "30m": "M30", "1h": "H1", "4h": "H4", "1d": "D1"}
_mt5_offsets = {}


def mt5_symbol(symbol):
    return norm(symbol).replace("/", "")


def _mt5_offset(symbol):
    """The terminal's server clock minus UTC, measured once from a live tick; with no fresh tick (market
    closed) the MetaQuotes rule (New York + 7 h) is used."""
    import mt5_client
    if symbol not in _mt5_offsets:
        try:
            _mt5_offsets[symbol] = mt5_client.detect_offset(mt5_symbol(symbol))
        except Exception:
            return None
    return _mt5_offsets[symbol]


def fetch_candles(symbol, interval="1h", count=150):
    """Oldest -> newest [{t,o,h,l,c}] mid prices, t = candle start (epoch s); the last one is still forming."""
    if _source() == "mt5":
        import mt5_client          # MT5 bars are bid prices, not mid: a half spread off, well inside any stop
        bars = mt5_client.bars(mt5_symbol(symbol), MT5_TF[interval], count, _mt5_offset(symbol))
        candles = [{"t": b["t"] // 1000, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]} for b in bars]
    elif _source() == "oanda":
        j = oanda(f"/v3/instruments/{instrument(symbol)}/candles?granularity={OANDA_GRANULARITY[interval]}"
                  f"&count={count}&price=M")
        candles = [{"t": int(float(c["time"])), **{k: float(c["mid"][k]) for k in "ohlc"}} for c in j["candles"]]
    else:
        yi, rng = YAHOO_RANGE[interval]
        r = _yahoo(symbol, yi, rng)
        q = r["indicators"]["quote"][0]
        rows = zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"])
        candles = [{"t": t, "o": o, "h": h, "l": lo, "c": c} for t, o, h, lo, c in rows if None not in (o, h, lo, c)]
        candles = _merge(candles, INTERVAL_SEC[yi])
        if interval == "4h":
            candles = _merge(candles, 14400, align=True)
    if len(candles) < 60:
        raise RuntimeError(f"only {len(candles)} {interval} candles for {symbol} from {_source()}")
    return candles[-count:]


def fetch_price(symbol):
    """Current mid price."""
    if _source() == "mt5":
        import mt5_client
        t = mt5_client.tick(mt5_symbol(symbol))
        return (float(t["bid"]) + float(t["ask"])) / 2
    if _source() == "oanda" and CFG["OANDA_ACCOUNT"]:
        p = oanda(f"/v3/accounts/{CFG['OANDA_ACCOUNT']}/pricing?instruments={instrument(symbol)}")["prices"][0]
        return (float(p["bids"][0]["price"]) + float(p["asks"][0]["price"])) / 2
    return float(_yahoo(symbol, "1m", "1d")["meta"]["regularMarketPrice"])


def _yahoo(symbol, interval, rng):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{norm(symbol).replace('/', '')}=X"
           f"?interval={interval}&range={rng}")
    return http_json(url)["chart"]["result"][0]


def _merge(candles, sec, align=False):
    """Fold candles into sec-second buckets: clock-aligned (4h from 1h), or folding the stray
    'latest tick' candle Yahoo appends into the candle it belongs to."""
    out = []
    for c in candles:
        t = c["t"] // sec * sec if align else c["t"]
        if out and (out[-1]["t"] == t if align else t - out[-1]["t"] < sec * 0.9):
            o = out[-1]
            o["h"], o["l"], o["c"] = max(o["h"], c["h"]), min(o["l"], c["l"]), c["c"]
        else:
            out.append({**c, "t": t})
    return out


class MockFeed:
    """Random-walk candles for plumbing tests; every get() adds one new candle stamped with the wall clock."""

    def __init__(self, seed=7, start=1.085, vol=0.0012, n=150):
        self.rng, self.vol = random.Random(seed), vol
        t0 = time.time() - (n + 1) * 3600
        self.candles = [{"t": t0, "o": start, "h": start, "l": start, "c": start}]
        for i in range(n):
            self._step(t0 + (i + 1) * 3600)

    def _step(self, t):
        g, o = self.rng.gauss, self.candles[-1]["c"]
        c = o * (1 + g(0, self.vol))
        self.candles.append({"t": t, "o": o, "c": c, "h": max(o, c) * (1 + abs(g(0, self.vol / 2))),
                             "l": min(o, c) * (1 - abs(g(0, self.vol / 2)))})
        self.candles = self.candles[-200:]

    def get(self):
        self._step(max(time.time(), self.candles[-1]["t"] + 1))
        return list(self.candles[-150:])


# ---------------------------------------------------------------- indicators
def ema(values, n):
    e = sum(values[:n]) / n
    for v in values[n:]:
        e += (v - e) * 2 / (n + 1)
    return e


def rsi(closes, n=14):
    d = [b - a for a, b in zip(closes, closes[1:])]
    gain, loss = sum(max(x, 0) for x in d[:n]) / n, sum(max(-x, 0) for x in d[:n]) / n
    for x in d[n:]:
        gain, loss = (gain * (n - 1) + max(x, 0)) / n, (loss * (n - 1) + max(-x, 0)) / n
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def atr(candles, n=14):
    tr = [max(c["h"] - c["l"], abs(c["h"] - p["c"]), abs(c["l"] - p["c"])) for p, c in zip(candles, candles[1:])]
    a = sum(tr[:n]) / n
    for x in tr[n:]:
        a = (a * (n - 1) + x) / n
    return a


def indicators(candles):
    closes = [c["c"] for c in candles]
    return {"ema20": ema(closes, 20), "ema50": ema(closes, 50), "rsi14": rsi(closes), "atr14": atr(candles)}


if __name__ == "__main__":
    sym = norm(sys.argv[1]) if len(sys.argv) > 1 else "EUR/USD"
    iv = sys.argv[2] if len(sys.argv) > 2 else "1h"
    cs, dp = fetch_candles(sym, iv), decimals(sym)
    ind = indicators(cs)
    print(f"{sym} {iv} from {_source()}  {now()}  market {'OPEN' if market_open() else 'CLOSED'}  "
          f"sessions {sessions()}  {hours_to_close():.1f}h to weekly close")
    for c in cs[-5:]:
        print(" ", time.strftime("%a %H:%M", time.gmtime(c["t"])), *(f"{c[k]:.{dp}f}" for k in "ohlc"))
    print(f"  EMA20 {ind['ema20']:.{dp}f}  EMA50 {ind['ema50']:.{dp}f}  RSI14 {ind['rsi14']:.1f}  "
          f"ATR14 {ind['atr14']:.{dp}f} ({ind['atr14'] / pip_size(sym):.1f} pips)  price now {fetch_price(sym):.{dp}f}")
