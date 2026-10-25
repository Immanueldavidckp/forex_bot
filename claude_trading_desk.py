#!/usr/bin/env python3
"""
claude_trading_desk.py - shared pieces of the forex desk, used by team/agent.py and team/conductor.py.

  parse_json  pull the JSON object out of an agent's reply
  mock_agent  stand-in desk member for plumbing tests (no Claude calls)
  guard       hard rules in code: the agents propose, this decides
  handoff     send the guarded order to the paper account, or to OpenClaw as a ticket
"""
import json, math, os, shlex, subprocess, time

import place_order as po
from llm_paper_trader import CFG, decimals, norm, notional_usd, pip_size, spread_pips, usd_per_unit

SIDE = {"buy": "long", "sell": "short"}
TICKETS = os.path.join(po.HERE, "tickets")
TICKET = """FOREX DESK ORDER TICKET {ticket}

Run exactly this one shell command, unchanged, exactly once:

{cmd}

Then reply with the JSON line it prints. Do not change any argument, do not retry, do not run anything else.
If it fails, reply with the error text and stop.
"""


def parse_json(text):
    """First JSON object in the reply, tolerating code fences or prose around it."""
    text, dec = text or "", json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict):
                return obj
    return {"error": "no JSON object in reply: " + text.strip()[:200]}


def num(x, default=math.nan):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


# ---------------------------------------------------------------- mock desk
def mock_agent(role, data):
    """Deterministic stand-in for each role, driven only by the indicators."""
    m, held = data["market"], (data.get("account") or {}).get("holding")
    price, atr, d = m["price"], m["atr14"], decimals(m["symbol"])
    trend = ("up" if m["ema20"] > m["ema50"] and price > m["ema20"] else
             "down" if m["ema20"] < m["ema50"] and price < m["ema20"] else "range")
    s = data.get("strategy") or {}
    if role == "research":
        return {"trend": trend, "strength": 0.3 if trend == "range" else 0.7, "support": m["low_24"],
                "resistance": m["high_24"], "stretched": abs(price - m["ema20"]) > 2 * atr,
                "summary": f"mock: {trend}, RSI {m['rsi14']}"}
    if role == "news":
        return {"sentiment": 0.0, "risk_event_next_24h": False, "next_event_hours": None, "events": [],
                "headlines": [], "summary": "mock: no news"}
    if role == "strategy":
        if held:
            out = (held["side"], trend) in (("long", "down"), ("short", "up"))
            return {"action": "close" if out else "hold", "size_pct": 0, "stop": held["stop"],
                    "target": held["target"], "confidence": 0.6,
                    "reasoning": "mock: trend turned against us" if out else "mock: let it run"}
        sgn = 1 if trend == "up" and m["rsi14"] < 70 else -1 if trend == "down" and m["rsi14"] > 30 else 0
        if not sgn:
            return {"action": "hold", "size_pct": 0, "stop": 0, "target": 0, "confidence": 0.5,
                    "reasoning": "mock: no setup"}
        return {"action": "buy" if sgn > 0 else "sell", "size_pct": 0.5, "stop": round(price - sgn * 1.5 * atr, d),
                "target": round(price + sgn * 3 * atr, d), "confidence": 0.7, "reasoning": f"mock: {trend} trend"}
    if role == "code":
        if s.get("action") not in SIDE:
            return {"valid": True, "reward_risk": 0, "stop_pips": 0, "stop_atr": 0, "issues": []}
        risk = abs(price - s["stop"])
        return {"valid": risk > 0, "reward_risk": round(abs(s["target"] - price) / risk, 2) if risk else 0,
                "stop_pips": round(risk / m["pip_size"], 1), "stop_atr": round(risk / atr, 2), "issues": []}
    if role == "risk":
        ok = (data.get("code") or {}).get("valid", False)
        return {"verdict": "approve" if ok else "reject", "size_pct": s.get("size_pct", 0), "reasons": ["mock"]}
    if role == "boss":
        r = data.get("risk") or {}
        act = s.get("action", "hold") if r.get("verdict") != "reject" or s.get("action") == "close" else "hold"
        return {"action": act, "size_pct": min(num(s.get("size_pct"), 0), num(r.get("size_pct"), 0)),
                "stop": s.get("stop", 0), "target": s.get("target", 0), "confidence": s.get("confidence", 0.5),
                "summary": f"mock: {act}"}
    return {"error": f"unknown role {role}"}


# ---------------------------------------------------------------- guard
def guard(reports, market, holding, budget, day_pnl=0.0):
    """Hard rules the agents cannot talk their way around; anything odd becomes HOLD.
    Closing an open position is always allowed. Opening one needs every check to pass,
    and the size in units is computed here, never by an agent."""
    boss = reports.get("boss")
    if not isinstance(boss, dict) or "error" in boss:
        return {"action": "hold", "why": f"boss reply unusable: {str(boss)[:80]}"}
    act, why = str(boss.get("action", "")).strip().lower(), str(boss.get("summary", ""))[:200]
    if act not in ("buy", "sell", "close", "hold"):
        return {"action": "hold", "why": f"boss action {act!r} is not buy/sell/close/hold"}
    if holding:                                     # never add to or flip a position; the opposite side means exit
        if act == "close" or (act in SIDE and SIDE[act] != holding["side"]):
            return {"action": "close", "side": holding["side"], "units": holding["units"], "why": why or "exit"}
        return {"action": "hold", "why": why or "keep the open position"}
    if act in ("hold", "close"):
        return {"action": "hold", "why": why or "no trade"}

    sym, side = market["symbol"], SIDE[act]
    price, atr, pip = num(market.get("price")), num(market.get("atr14")), pip_size(market["symbol"])
    stop, target = num(boss.get("stop")), num(boss.get("target"))
    strat, code, risk, news = ((reports.get(r) if isinstance(reports.get(r), dict) else {})
                               for r in ("strategy", "code", "risk", "news"))
    errs = [r for r, v in reports.items() if not isinstance(v, dict) or "error" in v]
    dist = abs(price - stop)
    rr = abs(target - price) / dist if dist > 0 else 0.0
    # an event flagged for the next 24h with no known time counts as imminent: the desk runs unattended
    event_h = num(news.get("next_event_hours"), 0.0 if news.get("risk_event_next_24h") is True else math.inf)
    min_stop = max(0.5 * atr, 4 * spread_pips(sym) * pip)
    checks = [
        (not errs, f"agent errors: {', '.join(errs)}"),
        (str(strat.get("action", "")).lower() == act, f"boss says {act} but strategy said {strat.get('action')}"),
        (code.get("valid") is True, "quant check failed: " + "; ".join(map(str, code.get("issues") or []))),
        (risk.get("verdict") in ("approve", "reduce"), f"risk verdict {risk.get('verdict')}"),
        (num(boss.get("confidence"), 0) >= float(CFG["MIN_CONFIDENCE"]),
         f"confidence {boss.get('confidence')} below {CFG['MIN_CONFIDENCE']}"),
        (day_pnl > -budget * float(CFG["DAILY_LOSS_LIMIT_PCT"]) / 100, f"daily loss limit hit ({day_pnl:+.2f})"),
        (event_h >= float(CFG["EVENT_BLACKOUT_HOURS"]),
         f"high-impact event in {event_h:.1f}h" if news.get("next_event_hours") is not None
         else "high-impact event due in 24h at an unknown time"),
        (not market.get("rollover_window"), "daily rollover window, spreads are wide"),
        (num(market.get("hours_to_weekly_close"), 99) >= 2, "too close to the weekly close"),
        ((stop < price < target) if side == "long" else (target < price < stop),
         f"{side} stop {stop} / target {target} on the wrong side of {price}"),
        (rr >= float(CFG["MIN_REWARD_RISK"]), f"reward:risk {rr:.2f} below {CFG['MIN_REWARD_RISK']}"),
        (min_stop <= dist <= 3 * atr, f"stop {dist / pip:.1f} pips away, allowed {min_stop / pip:.1f}-"
                                      f"{3 * atr / pip:.1f} (0.5-3 ATR, >= 4x spread)"),
    ]
    for ok, msg in checks:
        if not ok:
            return {"action": "hold", "why": f"guard: {msg}"[:200]}

    size = min(max(num(boss.get("size_pct"), 0), 0.0), 1.0)
    if not math.isnan(num(risk.get("size_pct"))):  # never more than risk signed off on
        size = min(size, max(num(risk.get("size_pct")), 0.0))
    per_unit = dist * usd_per_unit(sym, price)      # USD lost per unit if the stop is hit
    risk_usd = budget * float(CFG["RISK_PER_TRADE_PCT"]) / 100 * size
    cap = min(float(CFG["MAX_LEVERAGE"]) * budget, float(CFG["MAX_NOTIONAL_USD"]))
    units = int(min(risk_usd / per_unit, cap / notional_usd(sym, 1, price)) + 1e-9)   # 499.9999999 is 500
    if units < 1:
        return {"action": "hold", "why": f"guard: size rounds to 0 units (risk budget ${risk_usd:.2f})"}
    d = decimals(sym)
    return {"action": act, "side": side, "units": units, "size_pct": round(size, 2), "stop": round(stop, d),
            "target": round(target, d), "reward_risk": round(rr, 2), "risk_usd": round(units * per_unit, 2),
            "why": why}


# ---------------------------------------------------------------- handoff
def handoff(final, symbol, mode, price):
    """paper: fill in the local paper account right here.
    openclaw: write a ticket, let OpenClaw run place_order.py with it, then believe only what
    place_order.py recorded for that ticket - never OpenClaw's own account of what it did."""
    symbol = norm(symbol)
    order = {"ticket": "T" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + os.urandom(2).hex(),
             "cmd": "close" if final["action"] == "close" else "open", "symbol": symbol,
             "price": round(price, decimals(symbol))}
    if order["cmd"] == "open":
        order.update({k: final[k] for k in ("side", "units", "stop", "target")})
    if mode == "openclaw":
        return order, via_openclaw(order)
    if order["cmd"] == "open":
        return order, po.open_position(symbol, order["side"], order["units"], order["stop"], order["target"],
                                       order["price"], order["ticket"])
    return order, po.close_position(symbol, order["price"], "desk", order["ticket"])


def place_order_cmd(order):
    """The exact command line for a ticket; carries --simulate / --state so it does what this process would."""
    args = ["python3", os.path.join(po.HERE, "place_order.py")]
    if not po.LIVE:
        args.append("--simulate")
    if os.path.abspath(po.STATE_FILE) != po.DEFAULT_STATE:
        args += ["--state", os.path.abspath(po.STATE_FILE)]
    args += [order["cmd"], "--symbol", order["symbol"], "--price", str(order["price"]), "--ticket", order["ticket"]]
    if order["cmd"] == "open":
        args += ["--side", order["side"], "--units", str(order["units"]), "--stop", str(order["stop"]),
                 "--target", str(order["target"])]
    else:
        args += ["--reason", "desk"]
    return shlex.join(args)


def via_openclaw(order):
    os.makedirs(TICKETS, exist_ok=True)
    path = os.path.join(TICKETS, order["ticket"] + ".md")
    with open(path, "w") as f:
        f.write(TICKET.format(ticket=order["ticket"], cmd=place_order_cmd(order)))
    try:
        out = subprocess.run(shlex.split(CFG["OPENCLAW_CMD"]) + ["--message-file", path], capture_output=True,
                             text=True, timeout=int(CFG["OPENCLAW_TIMEOUT"]))
        reply = (out.stdout.strip() or out.stderr.strip())[-300:]
    except (OSError, subprocess.TimeoutExpired) as e:
        reply = f"{type(e).__name__}: {e}"[:300]
    rec = po.load()["tickets"].get(order["ticket"])
    if rec is None:
        return {"ok": False, "error": "OpenClaw did not execute the ticket", "openclaw": reply, "ticket": path}
    if rec.get("ok") and order["cmd"] == "open" and (rec.get("side"), rec.get("units")) != (order["side"],
                                                                                         order["units"]):
        rec = {**rec, "warning": "executed order differs from the ticket - check the account now"}
    return {**rec, "via": "openclaw"}
