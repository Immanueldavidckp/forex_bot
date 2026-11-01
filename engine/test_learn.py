"""engine/test_learn.py — the learning chart's store, matching and fit (no MT5, no files outside tmp_path)."""
import json
import os

import pytest

from engine import learn

TF = 900_000  # M15 in ms


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(learn, "LEARN_DIR", str(tmp_path))
    monkeypatch.setattr(learn, "LABELS_FILE", str(tmp_path / "labels.jsonl"))
    return tmp_path


def test_labels_survive_adds_notes_deletes_and_side_fixes(store, monkeypatch):
    monkeypatch.setattr(learn, "load_bars", lambda *a: [])
    a = learn.save_label({"sym": "COSMOS", "tf": "M15", "kind": "BOS", "side": "buy", "t0": 1000, "t1": 5000, "p0": 1.5})
    b = learn.save_label({"sym": "COSMOS", "tf": "M15", "kind": "FVG", "t0": 1000, "t1": 2000, "p0": 1.4, "p1": 1.45})
    learn.note_label(a["id"], "the first leg")
    learn.delete_label(b["id"])
    got = learn.labels("COSMOS", "M15")
    assert [r["id"] for r in got] == [a["id"]] and got[0]["note"] == "the first leg"
    learn._append({"op": "side", "id": a["id"], "side": "sell"})
    assert learn.labels("COSMOS", "M15")[0]["side"] == "sell"
    with pytest.raises(ValueError):
        learn.save_label({"sym": "../etc", "tf": "M15", "kind": "BOS", "t0": 1})


def test_infer_side_reads_where_price_came_from():
    tf = 900_000
    mk = lambda closes: [[i * tf, c, c + 1, c - 1, c] for i, c in enumerate(closes)]
    support = mk([10, 10.2, 10.1, 10.3, 10.1, 9.4])       # price lived above the level, then broke down
    resistance = mk([9, 8.9, 9.1, 8.8, 9.0, 10.6])        # price lived below the level, then broke up
    assert learn.infer_side(support, 0, 5 * tf, 9.8, "M15") == "sell"
    assert learn.infer_side(resistance, 0, 5 * tf, 9.9, "M15") == "buy"
    assert learn.infer_side([], 0, 5 * tf, 9.9, "M15") is None


def _det(events=(), zones=(), fvgs=(), swings=()):
    return {"n_bars": 99, "trend": None, "atr": 1.0, "events": list(events), "zones": list(zones),
            "fvgs": list(fvgs), "swings": list(swings)}


def test_compare_scores_ok_mixed_missed_and_extras(store, monkeypatch):
    ev_bos = {"kind": "BOS", "side": "buy", "level": 10.0, "level_t": 0, "t": 4 * TF, "close": 10.5}
    ev_choch = {"kind": "CHoCH", "side": "sell", "level": 50.0, "level_t": 90 * TF, "t": 95 * TF, "close": 49.0}
    ev_extra = {"kind": "CHoCH", "side": "buy", "level": 80.0, "level_t": 82 * TF, "t": 85 * TF, "close": 81.0}
    monkeypatch.setattr(learn, "detect", lambda *a, **k: _det(events=[ev_bos, ev_choch, ev_extra]))
    learn.save_label({"sym": "X", "tf": "M15", "kind": "BOS", "side": "buy", "t0": 0, "t1": 4 * TF, "p0": 10.1})     # ok
    learn.save_label({"sym": "X", "tf": "M15", "kind": "BOS", "side": "sell", "t0": 90 * TF, "t1": 95 * TF, "p0": 50.0})  # engine says CHoCH
    learn.save_label({"sym": "X", "tf": "M15", "kind": "CHoCH", "t0": 40 * TF, "p0": 200.0})                        # nothing there
    learn.save_label({"sym": "X", "tf": "M15", "kind": "region", "t0": 80 * TF, "t1": 99 * TF})                     # fully checked span
    c = learn.compare()
    assert c["per_kind"]["BOS"] == {"labels": 2, "ok": 1, "mixed": 1, "missed": 0}
    assert c["per_kind"]["CHoCH"]["missed"] == 1
    # inside the ✓ region: the mixed-kind break was still drawn by David (no extra), ev_extra was not (one extra)
    assert c["extras"]["CHoCH"] == 1 and c["extras"]["checked_ms"] == 19 * TF


def test_compare_matches_boxes_by_price_overlap(store, monkeypatch):
    z = {"kind": "supply", "top": 2.0, "bottom": 1.8, "t": 5 * TF, "side": "sell"}
    f = {"top": 1.6, "bottom": 1.5, "t": 5 * TF, "side": "sell"}
    monkeypatch.setattr(learn, "detect", lambda *a, **k: _det(zones=[z], fvgs=[f]))
    learn.save_label({"sym": "X", "tf": "M15", "kind": "supply", "t0": 4 * TF, "t1": 7 * TF, "p0": 1.82, "p1": 2.05})  # overlaps
    learn.save_label({"sym": "X", "tf": "M15", "kind": "FVG", "t0": 4 * TF, "t1": 7 * TF, "p0": 1.0, "p1": 1.1})       # wrong place
    c = learn.compare()
    assert c["per_kind"]["supply"]["ok"] == 1 and c["per_kind"]["FVG"]["missed"] == 1


def test_compare_scores_levels_and_trends(store, monkeypatch):
    sw = [{"t": 1 * TF, "price": 10.0, "kind": "low", "label": None},
          {"t": 3 * TF, "price": 12.0, "kind": "high", "label": None},
          {"t": 5 * TF, "price": 11.0, "kind": "low", "label": None},
          {"t": 7 * TF, "price": 13.0, "kind": "high", "label": None}]
    monkeypatch.setattr(learn, "detect", lambda *a, **k: _det(swings=sw))
    learn.save_label({"sym": "X", "tf": "M15", "kind": "support", "t0": 0, "t1": 2 * TF, "p0": 10.2})      # a swing low sits there
    learn.save_label({"sym": "X", "tf": "M15", "kind": "resistance", "t0": 0, "t1": 9 * TF, "p0": 99.0})   # nothing there
    learn.save_label({"sym": "X", "tf": "M15", "kind": "up trend", "t0": 0, "t1": 8 * TF})                 # HH + HL in the span
    learn.save_label({"sym": "X", "tf": "M15", "kind": "down trend", "t0": 0, "t1": 8 * TF})               # the engine reads up
    learn.save_label({"sym": "X", "tf": "M15", "kind": "sideways", "t0": 0, "t1": 1 * TF})                 # too few swings to say
    c = learn.compare()
    assert c["per_kind"]["support"]["ok"] == 1
    assert c["per_kind"]["resistance"]["missed"] == 1
    assert c["per_kind"]["up trend"]["ok"] == 1
    assert c["per_kind"]["down trend"]["mixed"] == 1
    assert c["per_kind"]["sideways"]["missed"] == 1


def test_fit_ranks_the_grid_and_writes_the_file(store, monkeypatch):
    ev = {"kind": "BOS", "side": "buy", "level": 10.0, "level_t": 0, "t": 4 * TF, "close": 10.5}
    monkeypatch.setattr(learn, "detect", lambda sym, tf, n=3000, swing_length=None: _det(events=[ev] if swing_length == 3 else []))
    learn.save_label({"sym": "X", "tf": "M15", "kind": "BOS", "side": "buy", "t0": 0, "t1": 4 * TF, "p0": 10.0})
    r = learn.fit()
    assert r["best"]["swing_length"] == 3 and r["best"]["recall"] == 1.0
    assert json.load(open(os.path.join(str(store), "fit.json")))["best"] == r["best"]
    from engine.config import STRATEGY
    # the live config is scored as the baseline, and fit restored the live knob afterwards
    assert r["live"]["swing_length"] == int(STRATEGY["swing_length"]) and "recall" in r["live"]
    assert STRATEGY["displacement_mult"] == r["live"]["displacement_mult"]
