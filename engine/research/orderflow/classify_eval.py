#!/usr/bin/env python3
"""
classify_eval.py — evaluate quote-only aggressor-side (buy/sell) classifiers on FxPro MT5 ticks.

Data: ~3 days of GOLD / EURUSD ticks (bid, ask, last, volume, flags) with NO trades, NO buy/sell flags,
constant `volume`.  So every "volume" below is a TICK COUNT (quote updates), and every "buy"/"sell" is an
ESTIMATE made from the direction of price changes — not real orders.

Methods (per tick sign s in {-1, 0, +1}; bar delta = sum of signs; CVD = cumsum of delta):
  bid_tt   : tick test on the bid: sign(dBid); unchanged -> carry previous non-zero sign (Lee-Ready tick test)
  mid_tt   : same on the mid-quote
  ask_tt   : same on the ask
  bid_chg  : sign(dBid), unchanged tick -> 0 (count quote updates only when the price changed)
  mid_chg  : same on the mid
  bvc_n    : Bulk Volume Classification on M1 bars, normal CDF  (Easley, Lopez de Prado, O'Hara 2012/2016)
  bvc_t    : BVC on M1 bars, Student-t CDF with nu = 0.25 (the ELO 2012 'Flow toxicity' setting)
  bvc_n5   : BVC on M5 bars directly, normal CDF
  last_q   : 'quote rule' on `last` vs mid (shown only to prove it is degenerate here: last == bid)

Tests: (a) agreement between methods; (b) delta vs own-bar return and NEXT-bar return (Pearson, Spearman,
sign hit rate; circular-shift permutation p-values + moving-block bootstrap CI); (c) bid-ask flicker and how
each method treats it; (d) timing of tick classification and of a day of M5 footprints.

numpy only (scipy used ONLY, if present, to self-check the Student-t CDF implementation).
"""
import gzip, os, sys, time, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('OF_DATA', '/tmp/claude-1000/-home-david-forex/6f79950b-2f79-4743-8184-d36a070b7e52/scratchpad/orderflow_data/')
CACHE = os.path.join(HERE, 'cache')
os.makedirs(CACHE, exist_ok=True)
SERVER_UTC_OFFSET_MS = 7_200_000          # FxPro server = EET (UTC+2) in this sample
RNG = np.random.default_rng(20261029)
RESULTS = {}

# ----------------------------------------------------------------------------------------------- loading

def load(sym):
    f = os.path.join(CACHE, sym + '.npz')
    if os.path.exists(f):
        z = np.load(f)
        return {k: z[k] for k in z.files}
    txt = gzip.open(DATA + sym + '_ticks.csv.gz', 'rt').read()
    body = txt[txt.index('\n') + 1:]
    a = np.fromstring(body.replace(',', ' '), sep=' ').reshape(-1, 7)
    d = dict(t=a[:, 0].astype(np.int64), bid=a[:, 1], ask=a[:, 2], last=a[:, 3], vol=a[:, 4], flags=a[:, 6].astype(np.int64))
    np.savez(f, **d)
    return d

# ----------------------------------------------------------------------------------------------- maths (numpy only)

def norm_cdf(x):
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))

def _betacf(a, b, x, iters=300):
    """Continued fraction for the incomplete beta function (modified Lentz), vectorised. Numerical Recipes 6.4."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = np.ones_like(x); d = 1.0 - qab * x / qap
    d = np.where(np.abs(d) < tiny, tiny, d); d = 1.0 / d; h = d.copy()
    for m in range(1, iters + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = np.where(np.abs(d) < tiny, tiny, d); c = 1.0 + aa / c; c = np.where(np.abs(c) < tiny, tiny, c)
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = np.where(np.abs(d) < tiny, tiny, d); c = 1.0 + aa / c; c = np.where(np.abs(c) < tiny, tiny, c)
        d = 1.0 / d; h *= d * c
    return h

def betainc(a, b, x):
    """Regularised incomplete beta I_x(a, b), vectorised in x (scalars a, b)."""
    x = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    with np.errstate(divide='ignore', invalid='ignore'):
        front = np.exp(lbeta + a * np.log(x) + b * np.log1p(-x))
        swap = x > (a + 1.0) / (a + b + 2.0)
        xs = np.where(swap, 1.0 - x, x)
        cf_direct = _betacf(a, b, np.where(swap, 0.5, x))
        cf_swap = _betacf(b, a, np.where(swap, xs, 0.5))
        out = np.where(swap, 1.0 - front * cf_swap / b, front * cf_direct / a)
    out = np.where(x <= 0, 0.0, out); out = np.where(x >= 1, 1.0, out)
    return out

def t_cdf(x, nu):
    x = np.asarray(x, dtype=float)
    ib = betainc(nu / 2.0, 0.5, nu / (nu + x * x))
    return np.where(x >= 0, 1.0 - 0.5 * ib, 0.5 * ib)

def selfcheck_tcdf():
    try:
        from scipy import stats
    except Exception:
        print('(scipy absent: Student-t CDF not cross-checked)'); return
    xs = np.array([-5, -2, -1, -0.5, -0.1, 0, 0.1, 0.5, 1, 2, 5, 20.0])
    for nu in (0.25, 1.0, 3.0):
        err = np.max(np.abs(t_cdf(xs, nu) - stats.t.cdf(xs, nu)))
        print('  t_cdf(nu=%.2f) max abs err vs scipy: %.2e' % (nu, err))

def rankdata(x):
    """Average ranks (ties averaged)."""
    x = np.asarray(x); n = len(x)
    order = np.argsort(x, kind='mergesort'); sx = x[order]
    ranks = np.empty(n); ranks[order] = np.arange(1, n + 1)
    # average tied ranks
    uniq, inv, cnt = np.unique(sx, return_inverse=True, return_counts=True)
    if len(uniq) < n:
        start = np.cumsum(np.r_[0, cnt[:-1]]) + 1
        avg = start + (cnt - 1) / 2.0
        ranks[order] = avg[inv]
    return ranks

def pearson(a, b):
    a = a - a.mean(); b = b - b.mean()
    den = math.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else float('nan')

def spearman(a, b):
    return pearson(rankdata(a), rankdata(b))

def sign_hit(a, b):
    m = (a != 0) & (b != 0)
    return float((np.sign(a[m]) == np.sign(b[m])).mean()) if m.sum() else float('nan'), int(m.sum())

def perm_pvalue(a, b, stat, n_perm=2000, min_shift=50):
    """Circular-shift permutation test: keeps each series' autocorrelation, destroys the alignment."""
    obs = stat(a, b); n = len(a)
    shifts = RNG.integers(min_shift, n - min_shift, size=n_perm)
    null = np.array([stat(a, np.roll(b, s)) for s in shifts])
    p = float((np.abs(null) >= abs(obs)).mean())
    return obs, p, float(null.std())

def block_bootstrap_ci(a, b, stat, block=12, n_boot=1000):
    n = len(a); nb = int(math.ceil(n / block)); vals = []
    for _ in range(n_boot):
        starts = RNG.integers(0, n - block + 1, size=nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
        vals.append(stat(a[idx], b[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))

# ----------------------------------------------------------------------------------------------- classifiers

def tick_test(p):
    """sign of price change, unchanged carries previous non-zero sign (first tick 0)."""
    s = np.sign(np.diff(p)); s = np.r_[0.0, s]
    nz = s != 0
    idx = np.where(nz, np.arange(len(s)), 0)
    np.maximum.accumulate(idx, out=idx)
    return s[idx]

def change_only(p):
    return np.r_[0.0, np.sign(np.diff(p))]

def bars_from_ticks(t_ms, price, bar_ms):
    """returns bar id per tick (int), unique bar ids, open/high/low/close/count arrays."""
    bid_ = t_ms // bar_ms
    ub, first, cnt = np.unique(bid_, return_index=True, return_counts=True)
    last_ = first + cnt - 1
    o = price[first]; c = price[last_]
    h = np.maximum.reduceat(price, first); l = np.minimum.reduceat(price, first)
    return bid_, ub, o, h, l, c, cnt

def bvc_bar_signs(t_ms, mid, bar_ms, cdf, sigma_window):
    """BVC: per bar, buy share = CDF(dP / sigma). dP = close - previous close; sigma = trailing std of dP.
    Returns per-tick 'sign' = 2*buyshare-1 of the tick's bar, so that sum over a bar = V*(buy-sell)."""
    bid_, ub, o, h, l, c, cnt = bars_from_ticks(t_ms, mid, bar_ms)
    dp = np.r_[0.0, np.diff(c)]
    # trailing std over previous `sigma_window` bars (full-sample std used until the window is filled)
    sig = np.full(len(dp), dp.std())
    cs = np.cumsum(dp); cs2 = np.cumsum(dp * dp)
    w = sigma_window
    if len(dp) > w:
        m1 = (cs[w:] - cs[:-w]) / w; m2 = (cs2[w:] - cs2[:-w]) / w
        sig[w:] = np.sqrt(np.maximum(m2 - m1 * m1, 1e-30))
    sig = np.where(sig > 0, sig, dp.std())
    buy = cdf(dp / sig)
    per_bar = 2.0 * buy - 1.0
    pos = np.searchsorted(ub, bid_)
    return per_bar[pos], ub, buy

# ----------------------------------------------------------------------------------------------- evaluation

def evaluate(sym, point, min_ticks=30):
    print('\n' + '=' * 100 + '\n%s\n' % sym + '=' * 100)
    d = load(sym)
    t = d['t'] - SERVER_UTC_OFFSET_MS; bid, ask, last, fl = d['bid'], d['ask'], d['last'], d['flags']
    mid = (bid + ask) / 2.0; n = len(t)
    R = RESULTS[sym] = {}
    span_h = (t[-1] - t[0]) / 3.6e6
    print('ticks %d, span %.1f h (UTC %s .. %s)' % (n, span_h, time.strftime('%Y-%m-%d %H:%M', time.gmtime(t[0] / 1000)), time.strftime('%Y-%m-%d %H:%M', time.gmtime(t[-1] / 1000))))

    # --- (d) basic rates / flicker ---------------------------------------------------------------------
    db = np.diff(bid); da = np.diff(ask); chg_b = db != 0; chg_a = da != 0
    sec = (t - t[0]) // 1000; per_s = np.bincount(sec); act = per_s[per_s > 0]
    bc = bid[np.r_[True, chg_b]]
    flick = float((bc[2:] == bc[:-2]).mean())
    sg = np.sign(np.diff(bc)); rev = float((sg[1:] * sg[:-1] < 0).mean())
    # flicker within a time window: up-move reversed to the same price within 1 s / 5 s
    tb = t[np.r_[True, chg_b]]
    back = bc[2:] == bc[:-2]; dt_back = (tb[2:] - tb[:-2])[back]
    facts = dict(ticks=n, span_h=span_h, ticks_per_active_s=float(act.mean()), p99_ticks_s=int(np.percentile(act, 99)),
                 max_ticks_s=int(act.max()), share_no_quote_change=float((~chg_b & ~chg_a).mean()),
                 share_bid_change=float(chg_b.mean()), share_sign_bid_ne_ask=float((np.sign(db) != np.sign(da)).mean()),
                 median_spread_pts=float(np.median(ask - bid) / point), last_eq_bid=float((last == bid).mean()),
                 bid_flicker_share=flick, bid_sign_reversal_share=rev,
                 flicker_back_within_1s=float((dt_back <= 1000).mean()), flicker_back_within_5s=float((dt_back <= 5000).mean()),
                 mean_abs_bid_step_pts=float(np.abs(db[chg_b]).mean() / point))
    R['facts'] = facts
    for k, v in facts.items():
        print('  %-28s %s' % (k, ('%.4f' % v) if isinstance(v, float) else v))

    # --- per-tick signs ---------------------------------------------------------------------------------
    t0 = time.time()
    S = {}
    S['bid_tt'] = tick_test(bid); S['mid_tt'] = tick_test(mid); S['ask_tt'] = tick_test(ask)
    S['bid_chg'] = change_only(bid); S['mid_chg'] = change_only(mid)
    S['last_q'] = np.where(last > mid, 1.0, np.where(last < mid, -1.0, 0.0))
    t_rules = time.time() - t0
    t0 = time.time()
    S['bvc_n'], _, _ = bvc_bar_signs(t, mid, 60_000, norm_cdf, 120)
    S['bvc_t'], _, _ = bvc_bar_signs(t, mid, 60_000, lambda x: t_cdf(x, 0.25), 120)
    S['bvc_n5'], _, _ = bvc_bar_signs(t, mid, 300_000, norm_cdf, 48)
    t_bvc = time.time() - t0
    R['timing'] = dict(tick_rules_s=t_rules, bvc_s=t_bvc)
    print('\n  per-tick classification time: tick rules %.2fs, BVC (3 variants) %.2fs for %d ticks' % (t_rules, t_bvc, n))
    carried = float(((S['bid_tt'] != 0) & (S['bid_chg'] == 0)).mean())
    print('  bid_tt: share of ticks whose sign is CARRIED from an earlier change (no price move on the tick): %.3f' % carried)
    print('  last_q: buy %.4f sell %.4f zero %.4f  -> degenerate (last == bid)' % ((S['last_q'] > 0).mean(), (S['last_q'] < 0).mean(), (S['last_q'] == 0).mean()))
    R['facts']['bid_tt_carried_share'] = carried

    # --- (c) flicker treatment: a bid up-tick followed (after k unchanged ticks) by the exact return ------
    # net delta contributed by such up-down pairs incl. the carried ticks between them
    chg_idx = np.r_[0, np.where(chg_b)[0] + 1]          # tick index of each bid change (0 = first tick)
    back_idx = np.where(bc[2:] == bc[:-2])[0]           # i such that change i+1 reverses change i
    i0 = chg_idx[back_idx]; i1 = chg_idx[back_idx + 1]; i2 = chg_idx[back_idx + 2] if False else None
    gap = i1 - i0                                        # ticks between the move and its reversal (>=1)
    pair_net_tt = (S['bid_tt'][i0] * gap + S['bid_tt'][i1])   # carried: up * gap, then -1
    print('  flicker pairs: %d; mean ticks between move and reversal %.1f; net delta per pair: bid_tt %.2f, bid_chg 0.00' % (
        len(i0), gap.mean(), pair_net_tt.mean()))
    R['facts']['flicker_pairs'] = int(len(i0)); R['facts']['flicker_gap_ticks'] = float(gap.mean()); R['facts']['flicker_net_tt'] = float(pair_net_tt.mean())

    # --- up/down asymmetry: why a tick-count CVD can drift away from price ---------------------------------
    up = db > 0; dn = db < 0
    asym = dict(n_up=int(up.sum()), n_down=int(dn.sum()), mean_up_step_pts=float(db[up].mean() / point),
                mean_down_step_pts=float(-db[dn].mean() / point), net_count=int(up.sum() - dn.sum()),
                price_change_pts=float((bid[-1] - bid[0]) / point))
    R['facts']['asymmetry'] = asym
    print('  up/down asymmetry: up-ticks %d (mean step %.2f pts), down-ticks %d (mean step %.2f pts); net count %+d while price moved %+.0f pts' % (
        asym['n_up'], asym['mean_up_step_pts'], asym['n_down'], asym['mean_down_step_pts'], asym['net_count'], asym['price_change_pts']))

    # --- bars + deltas ------------------------------------------------------------------------------------
    for bar_name, bar_ms, block in (('M1', 60_000, 30), ('M5', 300_000, 12), ('M15', 900_000, 8)):
        bid_, ub, o, h, l, c, cnt = bars_from_ticks(t, mid, bar_ms)
        pos = np.searchsorted(ub, bid_)
        D = {k: np.bincount(pos, weights=S[k], minlength=len(ub)) for k in S}
        ret = np.log(c / o); keep = cnt >= min_ticks
        # consecutive-bar requirement for "next" return
        nxt_ok = np.r_[np.diff(ub) == 1, False] & keep & np.r_[keep[1:], False]
        ret_next = np.r_[ret[1:], np.nan]
        tbl = R[bar_name] = dict(n_bars=int(keep.sum()), n_pairs=int(nxt_ok.sum()))
        print('\n  --- %s bars: %d kept (>= %d ticks), %d consecutive pairs for the next-bar test ---' % (bar_name, keep.sum(), min_ticks, nxt_ok.sum()))
        # (a) agreement matrix (sign agreement of bar delta, Pearson)
        meths = ['bid_tt', 'mid_tt', 'ask_tt', 'bid_chg', 'mid_chg', 'bvc_n', 'bvc_t', 'bvc_n5']
        print('  (a) sign agreement of bar delta (lower) / Pearson corr (upper):')
        print('      ' + ''.join('%9s' % m for m in meths))
        agree = {}
        for i, a in enumerate(meths):
            row = '%8s' % a
            for j, b in enumerate(meths):
                if i == j: row += '%9s' % '-'; continue
                x, y = D[a][keep], D[b][keep]
                if j > i: v = pearson(x, y); agree['%s|%s_r' % (a, b)] = v
                else: v, _ = sign_hit(x, y); agree['%s|%s_sign' % (a, b)] = v
                row += '%9.3f' % v
            print(row)
        tbl['agreement'] = agree
        # (b) delta vs own return / next return
        print('  (b) delta vs return: Pearson, Spearman [block-bootstrap 95%% CI], sign hit, perm p (circular shift)')
        print('      %-8s | %8s %8s %18s %7s %7s | %8s %8s %18s %7s %7s' % ('method', 'r_same', 'rho', 'rho CI', 'hit', 'p', 'r_next', 'rho', 'rho CI', 'hit', 'p'))
        for m in meths + ['last_q']:
            x = D[m][keep]; y = ret[keep]
            r1 = pearson(x, y); rho1, p1, _ = perm_pvalue(x, y, spearman, n_perm=400); ci1 = block_bootstrap_ci(x, y, spearman, block, 300); hit1, _ = sign_hit(x, y)
            x2 = D[m][nxt_ok]; y2 = ret_next[nxt_ok]
            r2 = pearson(x2, y2); rho2, p2, _ = perm_pvalue(x2, y2, spearman, n_perm=1000); ci2 = block_bootstrap_ci(x2, y2, spearman, block, 500); hit2, nn = sign_hit(x2, y2)
            tbl[m] = dict(r_same=r1, rho_same=rho1, rho_same_ci=ci1, hit_same=hit1, p_same=p1, r_next=r2, rho_next=rho2, rho_next_ci=ci2, hit_next=hit2, p_next=p2)
            print('      %-8s | %8.3f %8.3f [%7.3f,%7.3f] %7.3f %7.3f | %8.3f %8.3f [%7.3f,%7.3f] %7.3f %7.3f' % (m, r1, rho1, ci1[0], ci1[1], hit1, p1, r2, rho2, ci2[0], ci2[1], hit2, p2))
        # baselines for the next-bar test: own return -> next return ; delta residual (orthogonal to own return)
        x = ret[nxt_ok]; y = ret_next[nxt_ok]
        rho, p, _ = perm_pvalue(x, y, spearman, 1000); hit, _ = sign_hit(x, y)
        tbl['baseline_ret'] = dict(rho_next=rho, p_next=p, hit_next=hit)
        print('      %-8s | %8s %8s %18s %7s %7s | %8.3f %8.3f %18s %7.3f %7.3f   (own return -> next return)' % ('ret', '', '', '', '', '', pearson(x, y), rho, '', hit, p))
        for m in ('bid_chg', 'bvc_n'):
            xd = D[m][nxt_ok]; xr = ret[nxt_ok]
            beta = (xd * xr).sum() / (xr * xr).sum(); res = xd - beta * xr
            rho, p, _ = perm_pvalue(res, y, spearman, 1000); hit, _ = sign_hit(res, y)
            tbl[m + '_resid'] = dict(rho_next=rho, p_next=p, hit_next=hit)
            print('      %-8s | %8s %8s %18s %7s %7s | %8.3f %8.3f %18s %7.3f %7.3f   (%s residual after own return)' % (m[:5] + 'res', '', '', '', '', '', pearson(res, y), rho, '', hit, p, m))
        # normalised delta (delta / ticks) for the change-only rule
        xd = D['bid_chg'][nxt_ok] / cnt[nxt_ok]; rho, p, _ = perm_pvalue(xd, y, spearman, 1000); hit, _ = sign_hit(xd, y)
        tbl['bid_chg_norm'] = dict(rho_next=rho, p_next=p, hit_next=hit)
        print('      %-8s | %8s %8s %18s %7s %7s | %8.3f %8.3f %18s %7.3f %7.3f   (bid_chg delta / ticks)' % ('chg/n', '', '', '', '', '', pearson(xd, y), rho, '', hit, p))
        # CVD vs price (level) — just the correlation of CVD with mid close, for the record
        for m in ('bid_tt', 'bid_chg', 'bvc_n'):
            cvd = np.cumsum(D[m][keep]); tbl[m + '_cvd_vs_price_r'] = pearson(cvd, c[keep])
        print('      CVD vs close level Pearson: ' + ', '.join('%s %.3f' % (m, tbl[m + '_cvd_vs_price_r']) for m in ('bid_tt', 'bid_chg', 'bvc_n')))

    # --- (d) footprint timing: one day of M5 footprints ---------------------------------------------------
    day = (t // 86_400_000); ud, cd = np.unique(day, return_counts=True); d0 = ud[np.argmax(cd)]
    m = day == d0; tt = t[m]; mm = mid[m]; sb = S['bid_chg'][m]
    lvl = 10 * point if sym == 'GOLD' else 10 * point          # GOLD 0.10, EURUSD 1 pip
    t0 = time.time()
    bar = (tt // 300_000); bar -= bar.min()
    row = np.rint(mm / lvl).astype(np.int64); row -= row.min()
    key = bar * (row.max() + 1) + row
    uk, inv = np.unique(key, return_inverse=True)
    buy = np.bincount(inv, weights=(sb > 0), minlength=len(uk)); sell = np.bincount(inv, weights=(sb < 0), minlength=len(uk))
    tot = np.bincount(inv, minlength=len(uk))
    fp_bar = uk // (row.max() + 1); fp_row = uk % (row.max() + 1)
    dt_fp = time.time() - t0
    R['timing']['footprint_day_s'] = dt_fp; R['timing']['footprint_day_ticks'] = int(m.sum()); R['timing']['footprint_cells'] = int(len(uk))
    print('\n  (d) one day (%s, %d ticks) of M5 footprints at %.5g price step: %d bars x cells=%d in %.3fs' % (
        time.strftime('%Y-%m-%d', time.gmtime(d0 * 86400)), m.sum(), lvl, len(np.unique(fp_bar)), len(uk), dt_fp))
    # show one bar's footprint as an example
    bsel = np.unique(fp_bar)[len(np.unique(fp_bar)) // 2]; sel = fp_bar == bsel
    print('      example bar %d (bid_chg rule): price | buy | sell | total ticks' % bsel)
    for r_, b_, s_, tot_ in list(zip(fp_row[sel], buy[sel], sell[sel], tot[sel]))[::-1][:8]:
        print('        %10.5g | %4d | %4d | %4d' % ((r_ + np.rint(mm / lvl).min()) * lvl, b_, s_, tot_))


if __name__ == '__main__':
    print('Student-t CDF self-check:'); selfcheck_tcdf()
    evaluate('GOLD', 0.01)
    evaluate('EURUSD', 1e-5)
    with open(os.path.join(HERE, 'results.json'), 'w') as f:
        json.dump(RESULTS, f, indent=1, default=float)
    print('\nresults written to', os.path.join(HERE, 'results.json'))
