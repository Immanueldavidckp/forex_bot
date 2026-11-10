"""
concepter/kronos/model.py — load Kronos-base (the largest public Kronos; -large is not released) and draw forecast paths.

Runs in ~/opt/kronos-venv (torch + CUDA), not the engine's python. Kronos' own code lives in ~/opt/Kronos.
"""
from __future__ import annotations

import os
import sys
from typing import List

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/opt/Kronos"))
from model import Kronos, KronosPredictor, KronosTokenizer  # noqa: E402

COLS = ["open", "high", "low", "close", "volume"]


def load(name: str = "NeoQuasar/Kronos-base", device: str | None = None) -> KronosPredictor:
    """device None → the GPU when there is one (laptop GTX 1650), else the CPU (Oracle server); KRONOS_DEVICE overrides."""
    if device is None:
        import torch
        device = os.environ.get("KRONOS_DEVICE") or ("cuda:0" if torch.cuda.is_available() else "cpu")
    tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    mdl = Kronos.from_pretrained(name)
    tok.eval()
    mdl.eval()
    return KronosPredictor(mdl, tok, device=device, max_context=512)


def paths(pred: KronosPredictor, windows: List[pd.DataFrame], step: pd.Timedelta, pred_len: int,
          samples: int, batch: int = 64, T: float = 1.0, top_p: float = 0.9) -> np.ndarray:
    """windows: OHLCV frames (index = UTC bar times, same length). → closes, shape (len(windows), samples, pred_len).
    Each window is repeated `samples` times with sample_count=1, so every path is kept (Kronos' own
    sample_count averages them away)."""
    jobs = [(i, w) for i, w in enumerate(windows) for _ in range(samples)]
    out = np.zeros((len(windows), samples, pred_len), dtype=np.float64)
    fill = np.zeros(len(windows), dtype=int)
    for k in range(0, len(jobs), batch):
        chunk = jobs[k:k + batch]
        dfs = [w[COLS] for _, w in chunk]
        xs = [pd.Series(w.index) for _, w in chunk]
        ys = [pd.Series(pd.date_range(w.index[-1] + step, periods=pred_len, freq=step)) for _, w in chunk]
        res = pred.predict_batch(dfs, xs, ys, pred_len=pred_len, T=T, top_p=top_p, sample_count=1, verbose=False)
        for (i, _), r in zip(chunk, res):
            out[i, fill[i]] = r["close"].to_numpy()
            fill[i] += 1
    return out
