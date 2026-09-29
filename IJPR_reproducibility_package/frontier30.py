# -*- coding: utf-8 -*-
"""Resumable frontier sweep at thirty paired replications per point."""
import json, os, sys
import numpy as np
from dse_psd import simulate

N = 30
STORE = 'frontier30.json'
GRID = {'FSB':  ('d_fix', [0.30, 0.40, 0.50, 0.60, 0.70]),
        'FTV':  ('d_fix', [0.30, 0.40, 0.50, 0.60, 0.70]),
        'VOB':  ('d_base', [0.05, 0.10, 0.175, 0.25, 0.325, 0.40]),
        'PF-Full': ('d_base', [0.05, 0.10, 0.175, 0.25, 0.325, 0.40])}

def load():
    return json.load(open(STORE)) if os.path.exists(STORE) else {}

def todo():
    done = load()
    out = []
    for c, (kw, grid) in GRID.items():
        for g in grid:
            if '%s|%.3f' % (c, g) not in done:
                out.append((c, kw, g))
    return out

if __name__ == '__main__':
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    done = load()
    for c, kw, g in todo()[:budget]:
        rs = [simulate(1000 + s, c, **{kw: g}) for s in range(N)]
        f = lambda k: (float(np.mean([r[k] for r in rs])),
                       float(np.std([r[k] for r in rs], ddof=1)))
        done['%s|%.3f' % (c, g)] = dict(cond=c, knob=g, makespan=f('makespan'),
                                        exp30=f('exposure30'), viol=f('violations'))
        json.dump(done, open(STORE, 'w'), indent=1)
        print('  %-8s %.3f  span=%.0f  exp30=%.4f' %
              (c, g, done['%s|%.3f' % (c, g)]['makespan'][0],
               done['%s|%.3f' % (c, g)]['exp30'][0]), flush=True)
    print('remaining points: %d' % len(todo()))
