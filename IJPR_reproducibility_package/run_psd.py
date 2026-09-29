# -*- coding: utf-8 -*-
"""ISO/TS 15066 PSD baseline over paired replications."""
import json, sys
from dse_psd import simulate
N = 60
KEYS = ['makespan','violations','exposure30','exposure50','latched','decel_ep',
        'idle_ratio','slow_time']
for cond in sys.argv[1:]:
    per = {k: [] for k in KEYS}
    for s in range(N):
        m = simulate(1000 + s, cond)
        for k in KEYS: per[k].append(float(m[k]))
    json.dump(per, open('p_%s.json' % cond, 'w'))
    print('%s done (n=%d)' % (cond, N), flush=True)
