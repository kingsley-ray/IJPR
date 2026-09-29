# -*- coding: utf-8 -*-
"""Run one condition over N paired replications and store per-seed vectors."""
import json, sys
from dse_sim import simulate

N = 40
KEYS = ['makespan', 'violations', 'exposure30', 'exposure50', 'latched',
        'decel_ep', 'unnecessary_valid', 'precautionary', 'idle_ratio',
        'tier_sub', 'rejections', 'idle_from_reject', 'resched', 'slow_time',
        'interrupt_events', 'tasks_interrupted', 'stretch_mean']

for cond in sys.argv[1:]:
    per = {k: [] for k in KEYS}
    for s in range(N):
        m = simulate(1000 + s, cond)
        for k in KEYS:
            per[k].append(float(m[k]))
    json.dump(per, open('v_%s.json' % cond, 'w'))
    print('%s done (n=%d)' % (cond, N), flush=True)
