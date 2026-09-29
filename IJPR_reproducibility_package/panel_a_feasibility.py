# -*- coding: utf-8 -*-
"""Panel (a): prospective task-robot feasibility matrix at a real decision epoch.

Values are ξ̃_k(t_e | T_i) from Equation (14), read out of a PF-Full
replication (seed 1000) at t_e = 220.1 s, during the parallel
module-extraction phase in which T2 (material transfer) and T4
(sequential cooperation) are both eligible for both cobots.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from dse_sim import simulate

plt.rcParams.update({'font.family': 'serif', 'font.size': 8.5,
                     'axes.linewidth': 0.7, 'savefig.dpi': 400})

T_E = 220.1
NAVY = '#1F3864'

m = simulate(1000, 'PF-Full')
snap = min(m['probes'], key=lambda p: abs(p[0] - T_E))
t_e, vals = snap[0], snap[1]

# rows: low tier first, as in the original layout
ROWS = [('$T_4$, $m_4=2$', 'sequential'),
        ('$T_2$, $m_2=3$', 'transfer')]
COLS = [('R1: human-near', 'R1'), ('R2: human-far', 'R2')]

M = np.array([[vals[(rb, tier)] for _, rb in COLS] for _, tier in ROWS])

fig, ax = plt.subplots(figsize=(3.6, 3.1))
norm = TwoSlopeNorm(vmin=min(-0.10, M.min()), vcenter=0.0,
                    vmax=max(0.35, M.max()))
im = ax.imshow(M, cmap='RdYlGn', norm=norm, aspect='auto')

for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M[i, j]
        ok = v > 0
        ax.text(j, i, '%+.2f  %s' % (v, 'OK' if ok else 'X'),
                ha='center', va='center', fontsize=8, fontweight='bold',
                color=NAVY if ok else 'white')

ax.set_xticks(range(len(COLS)))
ax.set_xticklabels([c for c, _ in COLS], fontsize=7.5)
ax.set_yticks(range(len(ROWS)))
ax.set_yticklabels([r for r, _ in ROWS], fontsize=8)
ax.set_xlabel('Candidate pair $(T_i,\\,m_i)$', fontsize=8)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)

cb = fig.colorbar(im, ax=ax, fraction=0.055, pad=0.05)
cb.set_label(r'$\widetilde{\xi}_k(t_e \mid T_i)$', fontsize=8.5)
cb.ax.tick_params(labelsize=6.5, length=2)
cb.outline.set_visible(False)

fig.tight_layout()
fig.savefig('panelA_real.png', bbox_inches='tight')

print('epoch t_e = %.1f s' % t_e)
for (rl, tier) in ROWS:
    print('  %-18s' % rl.replace('$', ''),
          '  '.join('%s %+.3f' % (rb, vals[(rb, tier)]) for _, rb in COLS))
