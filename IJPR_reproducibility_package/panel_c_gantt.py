# -*- coding: utf-8 -*-
"""Panel (c): short-horizon schedule taken from an actual PF-Full replication."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

from dse_sim import simulate

plt.rcParams.update({'font.family': 'serif', 'font.size': 8,
                     'axes.linewidth': 0.7, 'savefig.dpi': 332})

BLUE = '#1F4E9C'        # ordinary admitted task
RED = '#C0392B'         # hazardous-tier task
STOP = '#7B8CA6'        # latched stop overlay
SLOW = '#BFD0E6'        # reduced-speed overlay
INTR = '#F2E6C9'        # operator-proximity window

TIER_COLOUR = {'hazardous': RED}

m = simulate(1000, 'PF-Full')
sched = m['sched']
ts = np.array([r[0] for r in m['s_series']])
s1 = np.array([r[1] for r in m['s_series']])
s2 = np.array([r[2] for r in m['s_series']])
span = m['makespan']
events = m['human_events']
S = {'R1': s1, 'R2': s2}

half = np.ceil(span / 2.0 / 60.0) * 60.0          # split on a round minute
WINDOWS = [(0.0, half), (half, np.ceil(span / 60.0) * 60.0)]

fig, axes = plt.subplots(len(WINDOWS), 1, figsize=(5.9, 3.05))
ROWS = {'R1': 1, 'R2': 0}

for ax, (t0, t1) in zip(axes, WINDOWS):
    # operator-proximity windows
    for (e0, e1, kind, _) in events:
        if e1 > t0 and e0 < t1 and kind in ('reach_in', 'linger'):
            ax.axvspan(max(e0, t0), min(e1, t1), color=INTR, lw=0, zorder=0)

    for rec in sched:
        a, b = rec['start'], rec['end'] or span
        if b <= t0 or a >= t1:
            continue
        a, b = max(a, t0), min(b, t1)
        y = ROWS[rec['robot']]
        col = TIER_COLOUR.get(rec['tier'], BLUE)
        ax.barh(y, b - a, left=a, height=0.52, color=col,
                edgecolor='white', linewidth=0.5, zorder=2)
        lbl = rec['task'].replace('T2_', 'T2,').replace('T4_', 'T4,')
        if b - a > (t1 - t0) * 0.048:
            ax.text((a + b) / 2, y, lbl, ha='center', va='center',
                    fontsize=6.6, color='white', zorder=4)

        # overlay the commanded-speed state inside the bar
        sel = (ts >= a) & (ts <= b)
        sv, tv = S[rec['robot']][sel], ts[sel]
        if sv.size:
            for lo, hi, colr, hatch in ((-0.01, 0.05, STOP, '///'),
                                        (0.05, 0.95, SLOW, None)):
                mask = (sv > lo) & (sv <= hi)
                if not mask.any():
                    continue
                edges = np.diff(mask.astype(int))
                starts = list(tv[1:][edges == 1])
                ends = list(tv[1:][edges == -1])
                if mask[0]:
                    starts = [tv[0]] + starts
                if mask[-1]:
                    ends = ends + [tv[-1]]
                for x0, x1 in zip(starts, ends):
                    if x1 - x0 < 1.0:
                        continue
                    ax.barh(y, x1 - x0, left=x0, height=0.52, color=colr,
                            hatch=hatch, edgecolor='white', linewidth=0.35,
                            zorder=3)

    ax.set_xlim(t0, t1)
    ax.set_ylim(-0.6, 1.6)
    ax.set_yticks([0, 1]); ax.set_yticklabels(['R2', 'R1'], fontsize=9)
    ax.tick_params(axis='x', labelsize=8)
    ax.grid(axis='x', color='0.88', lw=0.5, zorder=1)
    ax.set_axisbelow(True)
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)

axes[-1].set_xlabel('Short-horizon time [s]', fontsize=9.5)

handles = [Patch(facecolor=BLUE, label='task execution'),
           Patch(facecolor=RED, label='hazardous-tier task'),
           Patch(facecolor=SLOW, label='reduced speed'),
           Patch(facecolor=STOP, hatch='///', label='latched stop'),
           Patch(facecolor=INTR, label='operator proximity')]
axes[0].legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 1.30),
               ncol=5, frameon=False, fontsize=7.4, handlelength=1.2,
               columnspacing=1.0, handletextpad=0.4)

fig.tight_layout()
fig.subplots_adjust(top=0.86, hspace=0.40)
fig.savefig('panelC_compact.png', bbox_inches='tight', pad_inches=0.02)

import json
info = {}
for tid, pnom in (('T1', 110.0), ('T3', 70.0)):
    r = [x for x in sched if x['task'] == tid][0]
    el = r['end'] - r['start']
    info[tid] = dict(start=round(r['start'], 1), end=round(r['end'], 1),
                     elapsed=round(el, 1), nominal=pnom,
                     lost_pct=round(100 * (el - pnom) / pnom, 1))
info['makespan'] = round(span, 1)
info['R2_idle_until'] = round(min(x['start'] for x in sched
                                  if x['robot'] == 'R2'), 1)
print(json.dumps(info, indent=1))
