"""
concepters/demo — the plumbing demo. NOT a strategy, and it does not follow rules/supply_demand. It shows the
three things every concepter does, as small as possible, so a new one can be written by copying this file:

    1. read the chart       structure from the shared toolkit (David's BOS / CHoCH rule) → marks to draw
    2. take the trade       a BOS on the bar that just closed → open, SL at the move's start, TP at min_rr
                            (min_rr from the rules: how a concepter reads its strategy's numbers)
    3. manage / exit        +1R → stop to break-even (Modify); a break against the trade → Close
"""
from __future__ import annotations

from shared import toolkit as TK
from shared.contracts import Close, Decision, Modify, Open, View

from ..base import Concepter
from ..checks import check_manage, check_open


class DemoConcepter(Concepter):
    name = "demo"
    timeframes = ["M15"]
    lookback = 400

    def on_bar(self, view: View) -> Decision:
        bars = view.bars["M15"]
        if len(bars) < 50:
            return Decision(notes="not enough bars")
        m = TK.structure(bars)
        d = Decision(marks=TK.marks_for("M15", m, []))
        last = bars[-1]
        new = [e for e in m["events"] if e["t"] == last.t]
        mine = [p for p in view.positions if p.status == "open"]

        for p in mine:                                       # 3. manage / exit
            against = [e for e in new if e["side"] != p.side]
            risk = abs(p.entry - p.sl0)
            gain = (last.c - p.entry) if p.side == "buy" else (p.entry - (last.c + last.spread))
            if against:
                d.commands.append(Close(self.name, p.ticket, reason=f"{against[0]['kind']} against the trade"))
            elif risk and gain >= risk and p.sl != p.entry and (p.sl < p.entry if p.side == "buy" else p.sl > p.entry):
                d.commands.append(Modify(self.name, p.ticket, sl=p.entry, reason="+1R: stop to break-even"))

        if new and not view.positions:                       # 2. take the trade
            e = new[-1]
            entry = last.c + last.spread if e["side"] == "buy" else last.c
            sl = e["origin"]["price"]
            risk = abs(entry - sl)
            rr = float(self.rules.p("stops.min_rr", 2.0))
            tp = entry + rr * risk if e["side"] == "buy" else entry - rr * risk
            o = Open(self.name, view.symbol, e["side"], sl=sl, tp=tp,
                     reason=f"demo: {e['kind']} {e['side']} closed at {e['close']:g}, SL at the move's start")
            problems = check_open(o, view, self.rules)
            if problems:
                d.notes = "skipped: " + "; ".join(problems)
            else:
                d.commands.append(o)
        d.commands = [c for c in d.commands if isinstance(c, Open) or not check_manage(c, view)]
        return d
