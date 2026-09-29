# -*- coding: utf-8 -*-
"""Figure 5: comparison at the nominal setting (n = 60 paired replications).

Input : v_FSB.json, v_FTV.json, v_VOB.json, v_PF-Full.json   (run_conditions.py)
Output: fig5_bars.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'serif', 'font.size': 8.5,
                     'axes.linewidth': 0.7, 'savefig.dpi': 400})
C = ['FSB', 'FTV', 'VOB', 'PF-Full']
GREY = ['0.75', '0.60', '0.45', '0.15']
V = {c: json.load(open('v_%s.json' % c)) for c in C}
x = np.arange(4)


def ms(k):
    a = [np.array(V[c][k], float) for c in C]
    return [v.mean() for v in a], [v.std(ddof=1) for v in a]


PANEL_LABELS = []
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.4))
for j, (key, ylab, title, ylim) in enumerate([
        ('makespan', 'Makespan (s)', '(a) Throughput', (650, 820)),
        ('violations', 'Referee-confirmed violations',
         '(b) Threshold-crossing count', None),
        ('exposure30', 'Near-field exposure (m)',
         '(c) Speed-weighted exposure', None)]):
    m, e = ms(key)
    ax[j].bar(x, m, yerr=e, capsize=2.5, color=GREY, edgecolor='k', linewidth=0.6)
    ax[j].set_ylabel(ylab)
    PANEL_LABELS.append(title)
    if ylim:
        ax[j].set_ylim(*ylim)
for a in ax:
    a.set_xticks(x); a.set_xticklabels(C, rotation=20, fontsize=7.5)
    a.spines['top'].set_visible(False); a.spines['right'].set_visible(False)
fig.tight_layout()
# panel captions placed beneath each panel, below the tick labels
for a, lab in zip(ax, PANEL_LABELS):
    a.text(0.5, -0.34, lab, transform=a.transAxes, ha='center', va='top',
           fontsize=8.5)
fig.subplots_adjust(bottom=0.30)
fig.savefig('fig5_bars.png', bbox_inches='tight')
print('fig5_bars.png written')
