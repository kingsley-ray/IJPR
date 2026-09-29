# -*- coding: utf-8 -*-
"""Filter benefit as a function of ready-set tier heterogeneity."""
import json, sys
import numpy as np
from dse_sim import simulate, ready_heterogeneity

N = 20
HS = [0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0]

def run(hs):
    out = {}
    for h in hs:
        g = dict(width=12, hazard_frac=h)
        full = [simulate(2000 + s, 'PF-Full', graph=g) for s in range(N)]
        nof = [simulate(2000 + s, 'PF-NoFilter', graph=g) for s in range(N)]
        rec = dict(
            het=float(np.mean([ready_heterogeneity(m) for m in full])),
            rej=float(np.mean([m['rejections'] for m in full])),
            sub=float(np.mean([m['tier_sub'] for m in full])),
            viol_full=float(np.mean([m['violations'] for m in full])),
            viol_nof=float(np.mean([m['violations'] for m in nof])),
            exp_full=float(np.mean([m['exposure30'] for m in full])),
            exp_nof=float(np.mean([m['exposure30'] for m in nof])),
            span_full=float(np.mean([m['makespan'] for m in full])),
            span_nof=float(np.mean([m['makespan'] for m in nof])),
            d_viol=[float(a['violations'] - b['violations']) for a, b in zip(nof, full)],
            d_exp=[float(a['exposure30'] - b['exposure30']) for a, b in zip(nof, full)],
            d_span=[float(a['makespan'] - b['makespan']) for a, b in zip(nof, full)])
        out['%.2f' % h] = rec
        print('  h=%.2f het=%.2f rej=%5.1f sub=%4.2f  viol %.2f->%.2f  span %.0f->%.0f'
              % (h, rec['het'], rec['rej'], rec['sub'],
                 rec['viol_nof'], rec['viol_full'],
                 rec['span_nof'], rec['span_full']), flush=True)
    return out

if __name__ == '__main__':
    hs = [float(x) for x in sys.argv[1:]]
    json.dump(run(hs), open('het_%s.json' % '_'.join(sys.argv[1:]), 'w'), indent=1)
