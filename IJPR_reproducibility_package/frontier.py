# -*- coding: utf-8 -*-
"""Safety-productivity frontier: sweep each condition's conservatism knob."""
import json, sys
import numpy as np
from dse_sim import simulate

N = 12
FIX = [0.30, 0.40, 0.50, 0.60, 0.70]
BASE = [0.10, 0.175, 0.25, 0.325, 0.40]

def run(cond):
    pts = []
    grid = FIX if cond in ('FSB', 'FTV') else BASE
    for g in grid:
        kw = {'d_fix': g} if cond in ('FSB', 'FTV') else {'d_base': g}
        rs = [simulate(1000 + s, cond, **kw) for s in range(N)]
        f = lambda k: (float(np.mean([r[k] for r in rs])),
                       float(np.std([r[k] for r in rs], ddof=1)))
        pts.append(dict(knob=g, makespan=f('makespan'), exp30=f('exposure30'),
                        exp50=f('exposure50'), viol=f('violations')))
        print('  %s knob=%.3f span=%.0f exp30=%.3f' %
              (cond, g, pts[-1]['makespan'][0], pts[-1]['exp30'][0]), flush=True)
    return pts

if __name__ == '__main__':
    out = {}
    for c in sys.argv[1:]:
        out[c] = run(c)
    json.dump(out, open('frontier_%s.json' % '_'.join(sys.argv[1:]), 'w'), indent=1)
