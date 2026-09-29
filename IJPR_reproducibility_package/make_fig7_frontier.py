# -*- coding: utf-8 -*-
"""Figure 7: safety-productivity frontier.

Input : frontier_all.json   (frontier.py, run with dse_sim_results.py)
Output: fig7_frontier.png

Point labels give the swept conservatism parameter.  They are placed by a
greedy collision-avoiding search so that no two labels overlap.
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'serif', 'font.size': 8.5,
                     'axes.linewidth': 0.7, 'savefig.dpi': 350})

F = json.load(open('frontier_all.json'))
STYLE = {'FSB': ('o', '-', '0.55'), 'FTV': ('s', '-', '0.30'),
         'VOB': ('^', '--', '#C0392B'), 'PF-Full': ('D', '-', '#1F4E9C')}
ORDER = ['VOB', 'FSB', 'FTV', 'PF-Full']

fig, ax = plt.subplots(figsize=(5.6, 3.5))
for c in ORDER:
    pts = sorted(F[c], key=lambda p: p['makespan'][0])
    m, ls, col = STYLE[c]
    ax.plot([p['makespan'][0] for p in pts], [p['exp30'][0] for p in pts],
            marker=m, ls=ls, color=col, ms=4.5, lw=1.2, label=c,
            markerfacecolor='white' if c != 'PF-Full' else col, zorder=3)

ax.set_yscale('symlog', linthresh=0.01)
ax.set_xlabel('Makespan [s]  (lower is better)')
ax.set_ylabel('Near-field exposure  $\\int v_{robot}\\,dt$  for $d<0.30$ m  [m]\n'
              '(lower is better)', fontsize=7.5)
ax.axhline(0, color='0.85', lw=0.6)
ax.set_xlim(645, 855)
ax.legend(frameon=False, fontsize=7.5, loc='upper right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(alpha=0.25, lw=0.5)
fig.tight_layout()

# ---- greedy, collision-avoiding label placement ------------------------
fig.canvas.draw()
# candidate offsets, ordered per series so that a label stays on the side of
# its own curve: upper curves label upwards, lower curves downwards.
BIAS = {
    'VOB':     [(6, 6), (6, 16), (-26, 6), (-26, 16), (16, 6), (6, -12)],
    'FSB':     [(-8, 9), (2, 9), (-26, 9), (-8, 19), (10, 9), (-8, -14)],
    'FTV':     [(2, -14), (-26, -14), (2, -24), (12, -14), (-26, -24), (2, 9)],
    'PF-Full': [(8, -4), (8, 6), (8, -14), (-28, -4), (18, -4), (-28, 6)],
}
placed = []           # display-space boxes already occupied
W, H = 22.0, 10.0     # approximate label box in points

# markers and the polyline segments are both obstacles
for c in ORDER:
    pts = sorted(F[c], key=lambda q: q['makespan'][0])
    disp = [ax.transData.transform((q['makespan'][0], q['exp30'][0])) for q in pts]
    for xd, yd in disp:
        placed.append((xd - 5, yd - 5, xd + 5, yd + 5))
    for (x0, y0), (x1, y1) in zip(disp, disp[1:]):
        for i in range(1, 12):
            t = i / 12.0
            xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            placed.append((xs - 3, ys - 3, xs + 3, ys + 3))


def free(box):
    x0, y0, x1, y1 = box
    for a0, b0, a1, b1 in placed:
        if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
            return False
    return True


def overlap(box):
    x0, y0, x1, y1 = box
    a = 0.0
    for b0, c0, b1, c1 in placed:
        w = min(x1, b1) - max(x0, b0)
        h = min(y1, c1) - max(y0, c0)
        if w > 0 and h > 0:
            a += w * h
    return a


# fallback offsets stay close to the marker: a label near its own point with
# a small overlap is clearer than a well-separated label far from it
RING = [(6, 16), (6, -22), (-26, 16), (-26, -22), (18, 6), (-34, 6),
        (18, -14), (-34, -14)]
n_free, n_forced = 0, 0
for c in ORDER:
    col = STYLE[c][2]
    for p in sorted(F[c], key=lambda q: q['makespan'][0]):
        xd, yd = ax.transData.transform((p['makespan'][0], p['exp30'][0]))
        cands = BIAS[c] + RING
        best, best_a = None, None
        for dx, dy in cands:
            box = (xd + dx, yd + dy, xd + dx + W, yd + dy + H)
            # penalise distance from the marker so a close label wins ties
            a = overlap(box) + 0.20 * (abs(dx) + abs(dy)) ** 2
            if best_a is None or a < best_a:
                best, best_a = (dx, dy), a
        dx, dy = best
        ax.annotate('%.2f' % p['knob'], (p['makespan'][0], p['exp30'][0]),
                    textcoords='offset points', xytext=(dx, dy),
                    fontsize=5.8, color=col, zorder=5,
                    bbox=dict(boxstyle='square,pad=0.08', fc='white',
                              ec='none', alpha=0.9))
        placed.append((xd + dx, yd + dy, xd + dx + W, yd + dy + H))
        box = (xd + best[0], yd + best[1], xd + best[0] + W, yd + best[1] + H)
        if overlap(box) == 0.0:
            n_free += 1
        else:
            n_forced += 1
        placed.append(box)

fig.savefig('fig7_frontier.png', bbox_inches='tight')
print('fig7_frontier.png written; %d labels clear, %d least-overlap'
      % (n_free, n_forced))
