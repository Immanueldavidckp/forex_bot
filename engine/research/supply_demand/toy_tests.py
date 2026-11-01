#!/usr/bin/env python3
"""
toy_tests.py — behaviour checks for the six ports in ports.py (2026-10-30; rewritten 2026-10-30 09:xx after the
original was lost with the research scratchpad).

Each check is a fact taken from the ORIGINAL source as written up in opensource_report.md §2 — the box a tool draws,
when it counts a touch, what kills a zone — asserted on a toy series built to trigger exactly that path. They are
behaviour checks of the ports, not of supply & demand: nothing here says a zone is any good.

    python3 toy_tests.py          # prints every check, exits 1 on the first failure
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ports as P                                                                              # noqa: E402

FAIL = []


def check(name, cond, info=""):
    print(("  [ok] " if cond else "  [FAIL] ") + name + (f"  {info}" if info else ""))
    if not cond:
        FAIL.append(name)


def series(spec, n=None, flat=(100.0, 100.5, 99.5, 100.0)):
    """spec: {index: (o, h, l, c)} on a flat background; returns o, h, l, c arrays."""
    n = n or max(spec) + 40
    o, h, l, c = (np.full(n, x) for x in flat)
    for i, (oo, hh, ll, cc) in spec.items():
        o[i], h[i], l[i], c[i] = oo, hh, ll, cc
    return o, h, l, c


# ----------------------------------------------------------------------------------------------------------------
print("1. Shved Supply and Demand (mq4 14545 / mq5 29395)")
# ----------------------------------------------------------------------------------------------------------------
per = [(tf, P.shved_fractal_period(tf, 3.0), P.shved_fractal_period(tf, 6.0)) for tf in (1, 5, 15, 30, 60, 240, 1440)]
check("Fractal(): fast = 7 bars each side and slow = 15 on EVERY timeframe (the timeframe cancels)",
      all(f == 7 and s == 15 for _, f, s in per), str(per))

h_eq = np.array([1, 2, 3, 3, 2, 1.0])          # an equal high 1 bar BEFORE the candidate (older bars may be <=)
up, _ = P.shved_fractals(h_eq, -h_eq, 2)
h_eq2 = np.array([1, 2, 3, 3, 2, 1.0])[::-1]   # the same equal high AFTER it (newer bars must be strictly <)
up2, _ = P.shved_fractals(h_eq2, -h_eq2, 2)
check("fractal is asymmetric: an equal high in the OLDER bars is allowed, an equal high in the NEWER bars is not",
      bool(up[3]) and not bool(up2[2]), f"older-equal {up[3]}, newer-equal {up2[2]}")

o, h, l, c = series({30: (100.2, 104.0, 100.0, 103.5)}, n=90)
z = [z for z in P.shved(o, h, l, c, tf_minutes=15) if z["idx"] == 30][0]
atr7 = P.atr_rma(h, l, c, 7)[30]
check("box of an up fractal = High + 0.375 ATR7 down to max(min(Close, High-0.375ATR), High-0.75ATR)",
      abs(z["top"] - (104.0 + 0.375 * atr7)) < 1e-9 and abs(z["bottom"] - (104.0 - 0.375 * atr7)) < 1e-9,
      f"{z['bottom']:.4f}..{z['top']:.4f}, ATR7 {atr7:.4f}")
check("so the height is 0.75-1.125 ATR7 and it is anchored on the wick extreme, not the body",
      0.75 - 1e-9 <= (z["top"] - z["bottom"]) / atr7 <= 1.125 + 1e-9 and z["top"] > 104.0,
      f"{(z['top'] - z['bottom']) / atr7:.3f} ATR7")
check("no displacement / impulse / volume test anywhere: a lone fractal on a flat series is already a zone",
      z["strength"] == "untested" and z["hits"] == 0 and not z["turned"])

o, h, l, c = series({30: (100.2, 104.0, 100.0, 103.5), 50: (100.0, 105.0, 99.5, 100.0)}, n=90)   # one wick through
zs = P.shved(o, h, l, c, tf_minutes=15, include_busted=True)
turned = [q for q in zs if q["idx"] == 30]
check("a WICK through the far side turns the zone (resistance -> support), it is not closed through",
      len(turned) == 1 and turned[0]["turned"] and turned[0]["strength"] == "busted",
      "then the flat price below the box busts it a second time -> dropped, nothing is drawn")
check("a zone busted twice is simply gone (the original draws nothing for it)",
      not any(q["idx"] == 30 for q in P.shved(o, h, l, c, tf_minutes=15)))

# ----------------------------------------------------------------------------------------------------------------
print("2. cmike444 supply-and-demand-zones 1.3.1 (rally-base-drop)")
# ----------------------------------------------------------------------------------------------------------------
RBD_FLAT = [(100.0, 100.5, 99.5, 100.0)] * 20                       # ATR(14) = 1.0
RBD_RALLY = [(100.0, 103.2, 99.9, 103.0), (103.0, 106.2, 102.9, 106.0), (106.0, 109.2, 105.9, 109.0)]
RBD_BASE = [(109.0, 109.6, 108.8, 109.1), (109.1, 109.7, 108.9, 109.0)]
RBD_DROP = [(109.0, 109.2, 104.8, 105.0), (105.0, 105.2, 100.8, 101.0)]


def rbd(base=RBD_BASE, tail=[(101.0, 101.5, 100.5, 101.0)] * 10):
    spec = RBD_FLAT + RBD_RALLY + base + RBD_DROP + tail
    return (np.array([s[k] for s in spec]) for k in range(4))


o, h, l, c = rbd()
zs = P.cmike(o, h, l, c)
check("rally-base-drop found with the 4 patterns tried in order (RBD first)", len(zs) == 1 and zs[0]["type"] == "RBD",
      str([z["type"] for z in zs]))
z = zs[0]
check("supply box = lowest BODY of the base .. highest HIGH of the WHOLE formation (leg-in + base + leg-out)",
      z["proximal"] == min(min(b[0], b[3]) for b in RBD_BASE) and z["distal"] == float(h[20:27].max()),
      f"proximal {z['proximal']} distal {z['distal']} (base bodies 109.0/109.1, formation high {h[20:27].max()})")
check("explosive = body/range >= 0.7 AND range >= 1.5 x the local ATR of the 14 candles BEFORE the bar",
      z["known_idx"] == 26 and z["base_n"] == 2)
o2, h2, l2, c2 = rbd(base=RBD_BASE * 4)
check("a base longer than MAX_BASE_CANDLES (6) is not a zone", P.cmike(o2, h2, l2, c2) == [], "8 base candles")
o3, h3, l3, c3 = rbd(base=[(109.0, 111.0, 107.0, 109.1), (109.1, 111.1, 107.1, 109.0)])
check("isValidBase: a base taller than 1.5 x ATR is rejected (its high-low, not the box)",
      P.cmike(o3, h3, l3, c3) == [], "base 4.1 tall, ATR 1.0")
check("freshness: a zone never entered since the pattern ended is fresh", z["fresh"] and z["confidence"] > 0.5,
      f"confidence {z['confidence']:.3f}")
o4, h4, l4, c4 = rbd(tail=[(101.0, 101.5, 100.5, 101.0)] * 5 + [(101.0, 109.5, 100.5, 101.0)] * 5)
check("a later bar reaching the proximal makes it not fresh (freshness 1.0 -> 0.5, the only invalidation there is)",
      not P.cmike(o4, h4, l4, c4)[0]["fresh"])

# ----------------------------------------------------------------------------------------------------------------
print("3. Svopex S&D Scan (Pine v6)")
# ----------------------------------------------------------------------------------------------------------------
SVO = [(100.0, 100.5, 99.5, 100.0)] * 20 + [(100.0, 101.2, 99.8, 101.0)]      # ... then a NON-base candle
SVO_BASE = [(101.0, 101.6, 100.6, 101.1), (101.1, 101.7, 100.7, 101.0)]       # |c-o| 0.1 < 0.5 ATR
SVO_OUT = [(101.0, 104.2, 100.9, 104.0)]                                      # c-o = 3.0 > 1.5 ATR


def svo(base=SVO_BASE, tail=[(104.0, 104.5, 103.5, 104.0)] * 10):
    spec = SVO + base + SVO_OUT + tail
    return (np.array([s[k] for s in spec]) for k in range(4))


o, h, l, c = svo()
z = [q for q in P.svopex(o, h, l, c) if q["idx"] == 21][0]
check("zone = the base candles' WICK range (not bodies), anchored on the FIRST base bar",
      (z["bottom"], z["top"], z["side"], z["base_n"]) == (100.6, 101.7, "demand", 2))
check("the zone is handed on one bar late (sig[1]): known_idx = the explosive bar + 1",
      z["known_idx"] == z["expl_idx"] + 1, f"expl {z['expl_idx']} known {z['known_idx']}")
o2, h2, l2, c2 = svo(base=SVO_BASE * 2)
check("a base longer than baseMax (3) is discarded (baseCount := 0), no zone",
      not any(q["idx"] == 21 for q in P.svopex(o2, h2, l2, c2)), "4 base candles")
TOUCH = [(104.0, 104.5, 103.5, 104.0)] * 3 + [(104.0, 104.2, 101.5, 101.6)] + [(101.6, 102.0, 101.0, 101.8)] * 6
o3, h3, l3, c3 = svo(tail=TOUCH)
z0 = [q for q in P.svopex(o3, h3, l3, c3, break_pct=0) if q["idx"] == 21][0]
z100 = [q for q in P.svopex(o3, h3, l3, c3, break_pct=100) if q["idx"] == 21][0]
check("default breakPct 0: the zone is DELETED the first time a bar reaches its near edge (fresh-only tool)",
      z0["removed_idx"] == z0["touched_idx"] == 27, f"removed {z0['removed_idx']}")
check("breakPct 100: the same touch leaves it alive (removal needs the far edge)",
      z100["removed_idx"] is None and z100["touched_idx"] == 27)

# ----------------------------------------------------------------------------------------------------------------
print("4. Supply and Demand Zones | Flux Charts")
# ----------------------------------------------------------------------------------------------------------------
def flux_series(n=160, pivots=(60,)):
    o, h, l, c = series({}, n=n)
    for p in pivots:
        o[p], h[p], l[p], c[p] = 100.2, 104.0, 100.0, 103.5
    return o, h, l, c


o, h, l, c = flux_series()
z = P.flux(o, h, l, c)[0]
check("box = the pivot(30) HIGH down by the mean UPPER WICK of the pivot bar and the 4 before it (a tiny box)",
      (z["top"], z["bottom"]) == (104.0, 103.5) and z["known_idx"] == 60 + 30,
      f"{z['bottom']}..{z['top']}, mean upper wick 0.5")
o, h, l, c = flux_series(pivots=(60, 100))
check("a new zone overlapping an active zone of either side is skipped", len(P.flux(o, h, l, c)) == 1)

o, h, l, c = flux_series()
o[95:], h[95:], l[95:], c[95:] = 104.8, 105.3, 104.3, 104.9
z = P.flux(o, h, l, c)[0]
check("first close through the far edge = pendingFlip; still through on the next bar = breakout and the zone FLIPS side",
      z["first_break_idx"] == 95 and z["flip_idx"] == 96 and z["breakouts"] == 1 and z["is_supply"] is False
      and z["orig_supply"] is True)
o, h, l, c = flux_series()
o[95], h[95], l[95], c[95] = 100.0, 103.7, 99.8, 100.2
z = P.flux(o, h, l, c)[0]
check("a wick into the box with the close back outside is a RETEST, not a break (max one per 3 bars)",
      z["retests"] == 1 and z["breakouts"] == 0 and z["is_supply"] is True)
check("a Flux zone never dies: no mitigation, no invalidation — only the held statistic and the side flip",
      z["active"] and z["quality"] == (z["held"] + 1) / (z["resolved"] + 2))

# ----------------------------------------------------------------------------------------------------------------
print("5. Supply and Demand Zones [BigBeluga]")
# ----------------------------------------------------------------------------------------------------------------
def beluga(n=300, i0=250, vol_at=252, vol=5000.0):
    o, h, l, c = series({}, n=n)
    v = np.full(n, 100.0)
    o[i0], h[i0], l[i0], c[i0] = 100.0, 100.6, 99.4, 100.4          # the bull candle the box hangs on
    for k, i in enumerate((i0 + 1, i0 + 2, i0 + 3)):                # three bears
        o[i], h[i], l[i], c[i] = 100.0 - k, 100.2 - k, 99.4 - k, 99.6 - k
    v[vol_at] = vol
    return o, h, l, c, v


o, h, l, c, v = beluga()
z = P.bigbeluga(o, h, l, c, v)[0]
atr2 = P.atr_rma(h, l, c, 200) * 2
check("supply box = [low of the last BULL candle within 6 bars, that low + 2 x ATR(200)] — a fixed height, "
      "not the candle's range", (z["bottom"], z["idx"]) == (99.4, 250)
      and abs((z["top"] - z["bottom"]) - atr2[z["known_idx"]]) < 1e-9, f"{z['bottom']}..{round(z['top'], 4)}")
check("the trigger needs the PREVIOUS bar's volume above the 1000-bar average",
      P.bigbeluga(o, h, l, c, np.full(len(c), 100.0)) == [] and P.bigbeluga(*beluga(vol_at=251)[:4], beluga(vol_at=251)[4]) == [],
      "flat volume, and the spike one bar too early, both give nothing")
c2, h2 = c.copy(), h.copy()
c2[270], h2[270] = z["top"] + 1, z["top"] + 1.5
check("deleted on a CLOSE beyond the far edge", P.bigbeluga(o, h2, l, c2, v)[0]["deleted_idx"] == 270)

# ----------------------------------------------------------------------------------------------------------------
print("6. Supply Demand Zones PRO (ProjectSyndicate)")
# ----------------------------------------------------------------------------------------------------------------
def sdz(n=200, pivots=(50,), touches=()):
    o, h, l, c = series({}, n=n)
    for p in pivots:
        o[p], h[p], l[p], c[p] = 100.2, 104.0, 100.0, 103.5
    for t in touches:
        h[t] = 102.0
    return o, h, l, c


o, h, l, c = sdz()
z = P.sdzpro(o, h, l, c)[0]
atr20 = P.atr_rma(h, l, c, 20)[z["known_idx"]]
check("every zone is EXACTLY 1 ATR(20) tall, centred on the pivot candle's mid (forced up, then clamped down)",
      abs((z["top"] - z["bottom"]) - atr20) < 1e-9 and abs((z["top"] + z["bottom"]) / 2 - (104.0 + 100.0) / 2) < 1e-9,
      f"{round(z['bottom'], 4)}..{round(z['top'], 4)}, ATR20 {round(atr20, 4)}")
check("the zone is known at the pivot bar + swingLen (12), never earlier", z["known_idx"] == 50 + 12)
check("a second pivot of the same side within minZoneDistance (44 bars) gives no new zone",
      len(P.sdzpro(*sdz(pivots=(50, 70)))) == 1 and len(P.sdzpro(*sdz(pivots=(50, 110)))) == 2)
z = P.sdzpro(*sdz(touches=(70, 80, 90)))[0]
age = 199 - z["idx"]
check("strength = int(clamp(8 - 0.8 x retests - min(age/500, 2), 0, 10)) — fewer retests and younger = stronger",
      z["retests"] == 3 and z["strength"] == int(max(0, min(10, 8.0 - 0.8 * z["retests"] - min(age / 500.0, 2.0)))),
      f"retests {z['retests']} age {age} -> strength {z['strength']}")
o, h, l, c = sdz()
c[120], l[120] = 110.0, 103.0
check("broken on a CLOSE beyond the far edge (invalidation = Close), then it is grey 'historic'",
      P.sdzpro(o, h, l, c)[0]["broken_idx"] == 120)

print()
print(f"{len(FAIL)} failed" if FAIL else "ALL OK")
sys.exit(1 if FAIL else 0)
