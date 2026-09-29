# -*- coding: utf-8 -*-
"""Figure 7: safety-productivity frontier, thirty replications per point.

Input : frontier30_by_cond.json (frontier30.py), psd_compare.json (run_psd.py)
Output: fig7_frontier30.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'serif', 'font.size': 8.5,
                     'axes.linewidth': 0.7, 'savefig.dpi': 350})
F = json.load(open('frontier30_by_cond.json'))
PSD = json.load(open('psd_compare.json'))['PSD']
N = 30
STYLE = {'FSB': ('o', '-', '0.55'), 'FTV': ('s', '-', '0.30'),
         'VOB': ('^', '--', '#C0392B'), 'PF-Full': ('D', '-', '#1F4E9C')}

fig, ax = plt.subplots(figsize=(5.8, 3.7))
for c in ['VOB', 'FSB', 'FTV', 'PF-Full']:
    p = F[c]
    x = np.array([q['makespan'][0] for q in p])
    y = np.array([q['exp30'][0] for q in p])
    ye = np.array([q['exp30'][1] for q in p]) / np.sqrt(N) * 1.96
    xe = np.array([q['makespan'][1] for q in p]) / np.sqrt(N) * 1.96
    ylo = np.minimum(ye, y)          # the measure cannot be negative
    m, ls, col = STYLE[c]
    ax.errorbar(x, y, yerr=[ylo, ye], xerr=xe, marker=m, ls=ls, color=col,
                ms=4.5, lw=1.2, capsize=1.5, elinewidth=0.5, alpha=0.95,
                ecolor=col, label=c, zorder=3,
                markerfacecolor='white' if c != 'PF-Full' else col)

pm = float(np.mean(PSD['makespan']))
pe = float(np.mean(PSD['exposure30']))
pes = float(np.std(PSD['exposure30'], ddof=1)) / np.sqrt(len(PSD['exposure30'])) * 1.96
ax.errorbar([pm], [pe], yerr=[[min(pes, pe)], [pes]], marker='*', ms=11,
            color='#1B7837', capsize=1.5, elinewidth=0.5, ls='none', zorder=4,
            label='ISO/TS 15066 PSD (single setting,\nno tuning parameter)')

ax.set_yscale('symlog', linthresh=0.005)
ax.set_xlabel('Makespan [s]  (lower is better)')
ax.set_ylabel('Near-field exposure  $\\int v_{robot}\\,dt$  for $d<0.30$ m  [m]\n'
              '(lower is better)', fontsize=7.5)
ax.axhline(0, color='0.85', lw=0.6)
ax.axvline(740, color='0.75', ls=':', lw=0.8, zorder=1)
ax.annotate('crossover', (740, 4), textcoords='offset points', xytext=(4, 0),
            fontsize=6.5, color='0.35', rotation=90, va='top')
ax.legend(frameon=False, fontsize=6.8, loc='upper right', ncol=1,
          handlelength=1.6, labelspacing=0.75, borderpad=0.2)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(alpha=0.25, lw=0.5)
fig.tight_layout()
fig.savefig('fig7_frontier30.png', bbox_inches='tight')
print('written; error bars are 95 per cent CIs of the mean over %d replications' % N)
