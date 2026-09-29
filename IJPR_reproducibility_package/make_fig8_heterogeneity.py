# -*- coding: utf-8 -*-
"""Figure 8: tier heterogeneity - mechanism activation vs safety benefit.

Input : het_all.json   (het.py, run with dse_sim_generator.py)
Output: fig8_heterogeneity.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'serif', 'font.size': 8.5,
                     'axes.linewidth': 0.7, 'savefig.dpi': 350})
D = json.load(open('het_all.json'))
ks = sorted(D, key=float)
h = [float(k) for k in ks]
het = [D[k]['het'] for k in ks]
sub = [D[k]['sub'] for k in ks]
dv = [np.mean(D[k]['d_viol']) for k in ks]

rng = np.random.default_rng(5)
lo, hi = [], []
for k in ks:
    d = np.array(D[k]['d_viol'])
    b = rng.choice(d, (8000, len(d))).mean(axis=1)
    lo.append(np.percentile(b, 2.5)); hi.append(np.percentile(b, 97.5))

fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.8))
ax[0].plot(het, sub, 'o', color='#1F4E9C', ms=5)
z = np.polyfit(het, sub, 1)
xs = np.linspace(0, max(het), 20)
ax[0].plot(xs, np.polyval(z, xs), '-', color='#1F4E9C', lw=1, alpha=0.6)
ax[0].set_xlabel('ready-set tier heterogeneity')
ax[0].set_ylabel('tier substitutions per run')


ax[1].errorbar(h, dv, yerr=[np.array(dv) - np.array(lo), np.array(hi) - np.array(dv)],
               marker='s', color='#C0392B', ms=4.5, lw=1.1, capsize=2.5)
ax[1].axhline(0, color='0.4', lw=0.8, ls='--')
ax[1].set_xlabel('hazardous-tier fraction $h$')
ax[1].set_ylabel('$\\Delta$ violations  (no filter $-$ filter)')

for a in ax:
    a.spines['top'].set_visible(False); a.spines['right'].set_visible(False)
    a.grid(alpha=0.25, lw=0.5)
fig.tight_layout()
for a, lab in zip(ax, ['(a) the mechanism activates',
                       '(b) but safety does not improve']):
    a.text(0.5, -0.30, lab, transform=a.transAxes, ha='center', va='top',
           fontsize=8.5)
fig.subplots_adjust(bottom=0.28)
fig.savefig('fig8_heterogeneity.png', bbox_inches='tight')
print('corr(het, sub) = %.3f' % np.corrcoef(het, sub)[0, 1])
