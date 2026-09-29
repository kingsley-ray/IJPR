# -*- coding: utf-8 -*-
"""Paired analysis over common random numbers: Wilcoxon tests and bootstrap CIs."""
import json
import numpy as np
from scipy.stats import wilcoxon

rng = np.random.default_rng(7)
CONDS = ['FSB', 'FTV', 'VOB', 'PF-Full',
         'PF-NoFilter', 'PF-CompOnly', 'PF-Static', 'PF-RandTie']
V = {c: json.load(open('v_%s.json' % c)) for c in CONDS}
N = len(V['PF-Full']['makespan'])


def boot_ci(d, B=10000):
    idx = rng.integers(0, len(d), size=(B, len(d)))
    means = d[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired(a, b, key):
    """b - a, i.e. how the comparison condition differs from PF-Full."""
    x = np.array(V[a][key], float)
    y = np.array(V[b][key], float)
    d = y - x
    if np.allclose(d, 0):
        return dict(diff=0.0, lo=0.0, hi=0.0, p=1.0, note='identical')
    try:
        p = float(wilcoxon(y, x, zero_method='zsplit').pvalue)
    except ValueError:
        p = 1.0
    lo, hi = boot_ci(d)
    return dict(diff=float(d.mean()), lo=lo, hi=hi, p=p, note='')


KEYS = ['makespan', 'violations', 'exposure30', 'latched', 'decel_ep',
        'idle_ratio', 'rejections', 'idle_from_reject', 'resched', 'tier_sub']

print('n = %d paired replications (common random numbers)\n' % N)
print('=== Summary: mean [95%% bootstrap CI of the mean] ===')
hdr = '%-20s' % 'metric' + ''.join('%22s' % c for c in CONDS)
print(hdr)
for k in KEYS:
    row = '%-20s' % k
    for c in CONDS:
        d = np.array(V[c][k], float)
        lo, hi = boot_ci(d)
        row += '%22s' % ('%.3f [%.2f,%.2f]' % (d.mean(), lo, hi))
    print(row)

print('\n=== Paired comparisons against PF-Full  (positive = condition is higher) ===')
for k in ['makespan', 'violations', 'exposure30', 'latched', 'idle_ratio']:
    print('\n-- %s' % k)
    print('  %-14s %10s %22s %10s' % ('condition', 'Δ mean', '95% CI of Δ', 'p (Wilcoxon)'))
    for c in CONDS:
        if c == 'PF-Full':
            continue
        r = paired('PF-Full', c, k)
        star = '***' if r['p'] < 0.001 else '**' if r['p'] < 0.01 else \
               '*' if r['p'] < 0.05 else 'ns'
        print('  %-14s %10.3f   [%8.3f, %8.3f] %8.2g %s'
              % (c, r['diff'], r['lo'], r['hi'], r['p'], star))

print('\n=== Filter activity (PF-Full and ablations) ===')
for c in ['PF-Full', 'PF-NoFilter', 'PF-CompOnly', 'PF-Static', 'PF-RandTie']:
    rej = np.array(V[c]['rejections'], float)
    idl = np.array(V[c]['idle_from_reject'], float)
    sub = np.array(V[c]['tier_sub'], float)
    res = np.array(V[c]['resched'], float)
    print('  %-13s rejections %6.2f  idle-from-reject %5.2f s  '
          'substitutions %5.2f  epochs %7.1f  (runs with >=1 rejection: %d/%d)'
          % (c, rej.mean(), idl.mean(), sub.mean(), res.mean(),
             int((rej > 0).sum()), N))

json.dump({c: {k: [float(np.mean(V[c][k]))] + list(boot_ci(np.array(V[c][k], float)))
               for k in KEYS} for c in CONDS},
          open('stats_summary.json', 'w'), indent=1)
print('\nwritten stats_summary.json')
