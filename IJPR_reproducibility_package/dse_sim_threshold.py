# -*- coding: utf-8 -*-
"""
Computational evaluation of the safety-aware rolling-horizon framework.

Implements Equations (5)-(14) of the manuscript exactly, a workcell state
machine, the MWKR-EDD-SPT dispatcher, and an independent time-to-collision
referee that reads TRUE geometry while the safety layer reads OBSERVED
geometry (delayed, noisy, occlusion-prone).  All numerical parameters are
PLACEHOLDERS pending physical measurement; they are collected in PARAMS.
"""
import math
import random
from dataclasses import dataclass, field

import numpy as np

# =========================================================================
# PLACEHOLDER PARAMETERS  (to be replaced by measured values)
# =========================================================================
PARAMS = dict(
    dt=0.10,                 # control cycle [s]  (10 Hz)

    # --- safety layer ---------------------------------------------------
    D_base=0.25,             # residual protection margin [m]
    T_sys=0.12,              # camera-to-command latency, upper percentile [s]
    M_warn=0.25,             # slowdown buffer width [m]
    lam=0.15,                # per-cycle contraction fraction of the gap
    kappa_c=0.30,            # [m] per unit confidence deficit
    kappa_z=1.50,            # [m] per m of local depth deviation
    kappa_f=0.40,            # [m] per s of frame age
    T_dwell=0.60,            # stop-release dwell [s]
    rate_up=1.5,             # max d(s)/dt on re-acceleration [1/s]
    rate_dn=6.0,             # max |d(s)/dt| on deceleration [1/s]

    # --- task-context tiers  D_task(m) [m] ------------------------------
    tier={'independent': 0.00, 'sequential': 0.05,
          'transfer': 0.12, 'hazardous': 0.25},

    # --- robots ---------------------------------------------------------
    robots={
        'R1': dict(base=(-0.85, -0.15), T_act=0.10, a_eff=2.0, v_nom=0.45),
        'R2': dict(base=(0.85, -0.15), T_act=0.14, a_eff=1.6, v_nom=0.45),
    },

    # --- perception (observation model) ---------------------------------
    obs_delay=0.08,          # observation age [s]
    obs_noise=0.015,         # clearance measurement sd [m]
    occl_p=0.010,            # per-cycle probability of an occlusion episode
    occl_len=(4, 9),         # episode length [cycles]
    c_ok=0.95, c_occl=0.55,  # composite confidence
    z_ok=0.010, z_occl=0.045,  # local depth deviation [m]

    # --- referee (independent, reads TRUE geometry) ----------------------
    d_crit=0.20,             # hard critical clearance [m]
    ttc_crit=0.30,           # critical time-to-collision [s]
    ttc_safe=1.00,           # above this, no hazard was present

    # --- legacy fixed thresholds ----------------------------------------
    d_fix_stop=0.50, d_fix_slow=0.75,

    epoch_period=5.0,        # periodic rolling-horizon epoch [s]
    horizon_window=180.0,    # rolling-horizon window for due times [s]
)

TRAY = (0.0, 0.55)           # tray centre (x, y) [m]


# =========================================================================
# Geometry
# =========================================================================
def seg_seg_dist(p1, p2, q1, q2):
    """Shortest distance between two 2-D segments."""
    p1 = np.asarray(p1); p2 = np.asarray(p2)
    q1 = np.asarray(q1); q2 = np.asarray(q2)
    u = p2 - p1; v = q2 - q1; w = p1 - q1
    a = u @ u; b = u @ v; c = v @ v; d = u @ w; e = v @ w
    den = a * c - b * b
    if den < 1e-9:
        sc, tc = 0.0, (e / c if c > 1e-9 else 0.0)
    else:
        sc = (b * e - c * d) / den
        tc = (a * e - b * d) / den
    sc = min(1.0, max(0.0, sc)); tc = min(1.0, max(0.0, tc))
    return float(np.linalg.norm(w + sc * u - tc * v))


# =========================================================================
# Human motion: three scripted action classes
# =========================================================================
ACTIONS = ('reach_in', 'transit', 'linger')


class HumanScript:
    """Generates the TRUE operator geometry: torso, forearm, hand."""

    def __init__(self, rng, duration):
        self.rng = rng
        self.events = []
        t = rng.uniform(8.0, 18.0)
        while t < duration:
            kind = ACTIONS[rng.randrange(3)]
            dur = {'reach_in': 3.2, 'transit': 2.6, 'linger': 9.0}[kind]
            self.events.append((t, t + dur, kind, rng.uniform(-0.35, 0.35)))
            t += dur + rng.uniform(5.0, 15.0)

    def state(self, t):
        """Return (torso, elbow, hand) positions and the true hand velocity."""
        home = np.array([0.0, 1.70])
        pos, vel = home.copy(), np.zeros(2)
        for (t0, t1, kind, off) in self.events:
            if not (t0 <= t < t1):
                continue
            u = (t - t0) / (t1 - t0)
            tgt = np.array([TRAY[0] + off, TRAY[1] + 0.12])
            if kind == 'reach_in':                       # fast in-and-out
                s = math.sin(math.pi * u)
                pos = home + (tgt - home) * s
                vel = (tgt - home) * math.pi * math.cos(math.pi * u) / (t1 - t0)
            elif kind == 'transit':                      # lateral pass
                x = -1.5 + 3.0 * u
                pos = np.array([x, TRAY[1] + 0.55])
                vel = np.array([3.0 / (t1 - t0), 0.0])
            else:                                        # approach and linger
                s = min(1.0, u / 0.30)
                pos = home + (tgt - home) * s
                vel = ((tgt - home) / (0.30 * (t1 - t0))) if u < 0.30 else np.zeros(2)
            break
        d = pos - home
        nrm = np.linalg.norm(d)
        u_hat = d / nrm if nrm > 1e-6 else np.array([0.0, -1.0])
        hand = pos
        elbow = pos - 0.28 * u_hat
        torso = pos - 0.62 * u_hat
        return hand, elbow, torso, vel


# =========================================================================
# Robot kinematics (reduced: base -> elbow -> end-effector)
# =========================================================================
class Robot:
    def __init__(self, name, cfg):
        self.name = name
        self.base = np.array(cfg['base'])
        self.T_act = cfg['T_act']
        self.a_eff = cfg['a_eff']
        self.v_nom = cfg['v_nom']
        self.ee = self.base + np.array([0.0, 0.35])   # home
        self.prev_ee = self.ee.copy()
        self.s = 1.0
        self.latched = False
        self.dwell = 0.0
        self.task = None
        self.progress = 0.0
        self.path_u = 0.0

    def links(self):
        d = self.ee - self.base
        elbow = self.base + 0.5 * d
        return [(self.base, elbow), (elbow, self.ee)]

    def step_pose(self, target, dt):
        """Move the EE toward the task location at the commanded speed."""
        self.prev_ee = self.ee.copy()
        d = target - self.ee
        n = np.linalg.norm(d)
        step = self.v_nom * self.s * dt
        self.ee = target.copy() if n <= step or n < 1e-6 else self.ee + d / n * step

    def link_vel(self, dt):
        return (self.ee - self.prev_ee) / dt


# =========================================================================
# Tasks
# =========================================================================
@dataclass
class Task:
    tid: str
    p: float
    tier: str
    eligible: tuple
    pred: tuple
    loc: tuple
    due: float = 0.0
    done: bool = False
    started: bool = False
    assigned: str = None
    remaining: float = 0.0
    prescreen: float = 0.0          # human pre-screen delay before release
    ready_at: float = -1.0


def build_tasks(rng):
    """T1, T3, twelve T2 sub-tasks, twelve T4 sub-tasks (per-module precedence)."""
    T = {}
    T['T1'] = Task('T1', 110.0, 'independent', ('R1',), (),
                   (TRAY[0] - 0.30, TRAY[1] - 0.05))
    T['T3'] = Task('T3', 70.0, 'hazardous', ('R1',), (),
                   (TRAY[0] + 0.10, TRAY[1] + 0.02))
    for m in range(12):
        col, row = m % 6, m // 6
        loc = (TRAY[0] - 0.42 + 0.17 * col, TRAY[1] - 0.10 + 0.20 * row)
        T[f'T2_{m}'] = Task(f'T2_{m}', 42.0 + rng.uniform(0, 16.0), 'transfer',
                            ('R1', 'R2'), ('T1', 'T3'), loc)
        T[f'T4_{m}'] = Task(f'T4_{m}', 18.0 + rng.uniform(0, 8.0), 'sequential',
                            ('R1', 'R2'), (f'T2_{m}',),
                            (TRAY[0] + 0.55 + 0.10 * row, TRAY[1] - 0.35),
                            prescreen=8.0)
    total = sum(t.p for t in T.values())
    for t in T.values():                       # rolling-horizon due times
        t.due = PARAMS['horizon_window'] + 0.35 * total * rng.uniform(0.8, 1.2)
        t.remaining = t.p
    return T


def successors(T, tid):
    out, stack = set(), [tid]
    while stack:
        cur = stack.pop()
        for k, t in T.items():
            if cur in t.pred and k not in out:
                out.add(k); stack.append(k)
    return out


# =========================================================================
# Perception: TRUE -> OBSERVED
# =========================================================================
class Perception:
    def __init__(self, rng):
        self.rng = rng
        self.buf = []
        self.occl = 0
        self.frozen = None
        self.stale = 0.0

    def update(self, t, true_geom):
        P = PARAMS
        self.buf.append((t, true_geom))
        cutoff = t - P['obs_delay']
        while len(self.buf) > 1 and self.buf[1][0] <= cutoff:
            self.buf.pop(0)
        geom = self.buf[0][1]
        if self.occl > 0:
            self.occl -= 1
            self.stale += P['dt']
            geom = self.frozen
            conf, zdev = P['c_occl'], P['z_occl']
        else:
            if self.rng.random() < P['occl_p']:
                self.occl = self.rng.randint(*P['occl_len'])
                self.frozen = geom
            self.stale = P['obs_delay']
            conf, zdev = P['c_ok'], P['z_ok']
        return geom, conf, zdev, self.stale, (self.occl > 0)


# =========================================================================
# Safety layer  (Equations 5-12)
# =========================================================================
class SafetyLayer:
    """mode: 'full' | 'velocity_only' | 'fixed'"""

    def __init__(self, mode, params=None):
        self.P = params or PARAMS
        self.mode = mode
        self.env_prev = {}
        self.dbar_prev = {}

    def pair_boundary(self, key, d_obs, robot, link_v_proj, tier_margin,
                      conf, zdev, stale, tier_scale=1.0):
        P = self.P
        if self.mode == 'fixed':
            return P['d_fix_stop'], 0.0

        dbar = self.dbar_prev.get(key, d_obs)
        dbar = 0.7 * dbar + 0.3 * d_obs
        v_close = max(0.0, -(dbar - self.dbar_prev.get(key, dbar)) / P['dt'])
        self.dbar_prev[key] = dbar

        # ISO/TS 15066-aligned decomposition.  The human-travel term spans the
        # whole interval the robot needs to come to rest: system latency,
        # actuation delay and braking.  Human speed is separated from the
        # measured closing rate so that robot motion is not counted twice
        # (it enters only through D_stop).
        t_brake = link_v_proj / robot.a_eff
        v_human = max(0.0, v_close - link_v_proj)
        D_motion = v_human * (P['T_sys'] + robot.T_act + t_brake)         # Eq. (5)
        D_stop = (link_v_proj * robot.T_act
                  + link_v_proj ** 2 / (2.0 * robot.a_eff))               # Eq. (6)
        if self.mode == 'velocity_only':
            D_task = D_perc = 0.0
        else:
            D_task = tier_margin * tier_scale
            D_perc = (P['kappa_c'] * (1.0 - conf)
                      + P['kappa_z'] * zdev
                      + P['kappa_f'] * stale)                             # Eq. (7)
        D_raw = P['D_base'] + D_motion + D_stop + D_task + D_perc         # Eq. (8)

        prev = self.env_prev.get(key, D_raw)
        delta = max(0.0, prev - D_raw)
        D_env = D_raw + (1.0 - P['lam']) * delta                          # Eq. (9)
        self.env_prev[key] = D_env
        return D_env, v_close


# =========================================================================
# One simulation run
# =========================================================================
def simulate(seed, condition, tier_scale=1.0, duration=2200.0,
             d_base=None, d_fix=None):
    P = dict(PARAMS)
    if d_base is not None:
        P['D_base'] = d_base
    if d_fix is not None:
        P['d_fix_stop'] = d_fix
        P['d_fix_slow'] = d_fix + 0.25
    rng = random.Random(seed)
    nrng = random.Random(seed + 7919)

    ABL = {
        # condition        reschedule  safety_events  smooth  filter  ranked  mode
        'FSB':            (False, False, False, True,  True,  'fixed'),
        'FTV':            (True,  True,  True,  True,  True,  'fixed'),
        'VOB':            (True,  True,  True,  True,  True,  'velocity_only'),
        'PF-Full':        (True,  True,  True,  True,  True,  'full'),
        # --- ablations of the proposed framework -------------------------
        'PF-NoFilter':    (True,  True,  True,  False, True,  'full'),
        'PF-CompOnly':    (True,  False, True,  True,  True,  'full'),
        'PF-Static':      (False, False, True,  True,  True,  'full'),
        'PF-RandTie':     (True,  True,  True,  True,  False, 'full'),
    }
    (reschedule, safety_events, smooth, use_filter, ranked, mode) = ABL[condition]
    prospective = (mode == 'full') and use_filter

    T = build_tasks(rng)
    human = HumanScript(rng, duration)
    percep = Perception(nrng)
    safety = SafetyLayer(mode, P)
    robots = {n: Robot(n, c) for n, c in P['robots'].items()}

    mwkr = {k: sum(T[s].p for s in successors(T, k)) for k in T}

    fixed_order = (['T1', 'T3'] + [f'T2_{m}' for m in range(12)]
                   + [f'T4_{m}' for m in range(12)])

    t = 0.0
    M = dict(makespan=None, busy={n: 0.0 for n in robots}, latched=0,
             slow_time=0.0, decel_ep=0, unnecessary=0, violations=0,
             tier_sub=0, tier_sub_ok=0, resched=0, holds=0, _viol_prev=False,
             unnecessary_valid=0, precautionary=0,
             rejections=0, idle_from_reject=0.0,
             _latched_prev=False, _zone_prev=False,
             exposure20=0.0, exposure25=0.0, exposure30=0.0,
             exposure35=0.0, exposure40=0.0, exposure50=0.0, v_at_closest=0.0,
             d_min_true=9.9, near_time=0.0)
    M['sched'] = []
    M['s_series'] = []
    M['probes'] = []
    episode = None          # (start_time, min_true_ttc)
    prev_any_slow = False
    trace = []

    def true_geom():
        hand, elbow, torso, vel = human.state(t)
        return (hand, elbow, torso, vel)

    def clearances(geom, rb):
        """Pairwise clearances between robot links and human segments."""
        hand, elbow, torso, _ = geom
        hseg = [(hand, elbow), (elbow, torso)]
        out = []
        for li, L in enumerate(rb.links()):
            for hj, H in enumerate(hseg):
                out.append(((li, hj), seg_seg_dist(L[0], L[1], H[0], H[1])))
        return out

    while t < duration:
        tg = true_geom()
        og, conf, zdev, stale, degraded = percep.update(t, tg)

        # ---------------- safety layer, per robot ------------------------
        xi = {}
        for n, rb in robots.items():
            v_link = rb.link_vel(P['dt'])
            worst = 1.0
            for (key, d_obs) in clearances(og, rb):
                hand = og[0]
                approach = hand - rb.ee
                na = np.linalg.norm(approach)
                v_proj = max(0.0, float(v_link @ (approach / na))) if na > 1e-6 else 0.0
                tier_m = P['tier'][T[rb.task].tier] if rb.task else P['tier']['independent']
                D_safe, _ = safety.pair_boundary((n,) + key, d_obs, rb, v_proj,
                                                 tier_m, conf, zdev, stale,
                                                 tier_scale)
                if mode == 'fixed':
                    m_w = P['d_fix_slow'] - P['d_fix_stop']
                else:
                    m_w = P['M_warn']
                worst = min(worst, max(0.0, min(1.0, (d_obs - D_safe) / m_w)))  # Eq. (11)
            xi[n] = worst

        # ---------------- command generation (Eq. 12) --------------------
        any_slow = False
        for n, rb in robots.items():
            x = xi[n]
            if x <= 0.0:
                if not rb.latched:
                    M['latched'] += 1
                rb.latched, rb.dwell, s_t = True, 0.0, 0.0
            elif rb.latched:
                rb.dwell += P['dt']
                if rb.dwell >= P['T_dwell']:
                    rb.latched = False
                s_t = 0.0 if rb.latched else 3 * x * x - 2 * x ** 3
            else:
                s_t = 3 * x * x - 2 * x ** 3 if smooth else (1.0 if x > 0 else 0.0)
            lim = P['rate_up'] if s_t > rb.s else P['rate_dn']
            rb.s = max(0.0, min(1.0, rb.s + max(-lim * P['dt'],
                                                min(lim * P['dt'], s_t - rb.s))))
            if rb.task and rb.s < 0.99:
                any_slow = True
                M['slow_time'] += P['dt']

        # ---------------- referee layer (TRUE geometry) ------------------
        hand, _, _, hvel = tg
        d_true, ttc = 1e9, 1e9
        for n, rb in robots.items():
            for (_, d) in clearances(tg, rb):
                d_true = min(d_true, d)
            approach = rb.ee - hand
            na = np.linalg.norm(approach)
            if na > 1e-6:
                closing = float(hvel @ (approach / na)) + rb.v_nom * rb.s
                if closing > 1e-3:
                    ttc = min(ttc, na / closing)
        # speed-weighted exposure: robot speed integrated while inside d_crit
        for n, rb in robots.items():
            if not rb.task:
                continue
            dn = min(dd for (_, dd) in clearances(tg, rb))
            v = rb.s * rb.v_nom
            for thr in (0.20, 0.25, 0.30, 0.35, 0.40):
                if dn < thr:
                    M['exposure%d' % round(thr * 100)] += v * P['dt']
            if dn < 0.50:
                M['exposure50'] += v * P['dt']
                M['near_time'] += P['dt']
        if d_true < M['d_min_true']:
            M['d_min_true'] = d_true
            M['v_at_closest'] = max((rb.s * rb.v_nom) for rb in robots.values()
                                    if rb.task) if any(rb.task for rb in robots.values()) else 0.0

        moving = any(rb.s > 0.05 and rb.task for rb in robots.values())
        viol_now = moving and (d_true < P['d_crit'] or ttc < P['ttc_crit'])
        if viol_now and not M['_viol_prev']:
            M['violations'] += 1
        M['_viol_prev'] = viol_now

        if any_slow and not prev_any_slow:
            episode = [t, ttc, degraded]
        elif any_slow and episode:
            episode[1] = min(episode[1], ttc)
            episode[2] = episode[2] or degraded
        elif (not any_slow) and prev_any_slow and episode:
            M['decel_ep'] += 1
            if episode[1] > P['ttc_safe']:
                M['unnecessary'] += 1
                if episode[2]:
                    M['precautionary'] += 1      # taken under degraded sensing
                else:
                    M['unnecessary_valid'] += 1  # taken under valid sensing
            episode = None
        prev_any_slow = any_slow

        # ---------------- scheduling layer -------------------------------
        # ---- rolling-horizon triggers, Section 4.6 ----------------------
        # A task completion, a periodic epoch, or (when enabled) a
        # safety event.  An idle robot alone is NOT a trigger; it waits for
        # the next epoch, which is what makes the trigger set testable.
        ev_completion = any(rb.task and T[rb.task].remaining <= 0
                            for rb in robots.values())
        ev_periodic = (round(t / P['dt']) % int(P['epoch_period'] / P['dt']) == 0)
        latched_now = any(rb.latched for rb in robots.values())
        ev_interrupt = latched_now and not M['_latched_prev']
        M['_latched_prev'] = latched_now
        zone_now = any(
            any(dd < P['d_fix_slow'] if mode == 'fixed' else
                dd < safety.env_prev.get((n,) + key, 0.0) + P['M_warn']
                for (key, dd) in clearances(og, rb))
            for n, rb in robots.items() if rb.task)
        ev_zone = zone_now and not M['_zone_prev']
        M['_zone_prev'] = zone_now
        ev_safety = ev_interrupt or ev_zone
        # FSB reacts only to task completion; the other conditions also
        # re-invoke the scheduler on safety events (Section 4.6).
        events = (ev_completion or ev_periodic
                  or (safety_events and ev_safety))

        if events and prospective:
            # tiers for which at least one task is actually a ready candidate
            ready_tiers = set()
            for k, tk in T.items():
                if tk.done or tk.assigned:
                    continue
                if not all(T[q].done for q in tk.pred):
                    continue
                if tk.prescreen > 0 and tk.pred:
                    if t < max(T[q].ready_at for q in tk.pred) + tk.prescreen:
                        continue
                ready_tiers.add(tk.tier)
            snap = {}
            for n, rb in robots.items():
                for tname, tm in P['tier'].items():
                    if tname not in ready_tiers:
                        continue
                    worst = 1.0
                    for (key, d_obs) in clearances(og, rb):
                        D_t, _ = safety.pair_boundary(('snap', n, tname) + key,
                                                      d_obs, rb, 0.0, tm,
                                                      conf, zdev, stale, tier_scale)
                        worst = min(worst, (d_obs - D_t) / P['M_warn'])
                    snap[(n, tname)] = worst
            M['probes'].append((t, snap, {n: (rb.task is None)
                                          for n, rb in robots.items()},
                                sorted(ready_tiers)))

        if events:
            if reschedule:
                M['resched'] += 1
            for n, rb in robots.items():
                if rb.task and T[rb.task].remaining <= 0:
                    T[rb.task].done = True
                    T[rb.task].ready_at = t
                    for rec in M['sched']:
                        if rec['task'] == rb.task and rec['end'] is None:
                            rec['end'] = t
                    rb.task = None

            for n, rb in robots.items():
                if rb.task is not None or rb.latched:
                    continue
                cands = []
                for k, tk in T.items():
                    if tk.done or tk.assigned or n not in tk.eligible:
                        continue
                    if not all(T[q].done for q in tk.pred):
                        continue
                    if tk.prescreen > 0 and tk.pred:
                        if t < max(T[q].ready_at for q in tk.pred) + tk.prescreen:
                            continue
                    if not reschedule or condition == 'PF-Static':
                        nxt = next((f for f in fixed_order
                                    if not T[f].done and not T[f].assigned
                                    and n in T[f].eligible
                                    and all(T[q].done for q in T[f].pred)), None)
                        if k != nxt:
                            continue
                    # ---- prospective-tier feasibility, Eqs. (13)-(14) ----
                    if prospective:
                        tm = P['tier'][tk.tier]
                        ok = True
                        for (key, d_obs) in clearances(og, rb):
                            D_t, _ = safety.pair_boundary(
                                ('probe', n) + key, d_obs, rb, 0.0, tm,
                                conf, zdev, stale, tier_scale)
                            if d_obs - D_t <= 0:
                                ok = False
                                break
                        if not ok:
                            cands.append((None, k))      # rejected
                            continue
                    elif use_filter and xi[n] <= 0:
                        continue
                    cands.append((True, k))
                adm = [k for ok, k in cands if ok]
                rej = [k for ok, k in cands if ok is None]
                M['rejections'] += len(rej)
                if rej and not adm:
                    M['idle_from_reject'] += P['dt']
                if rej and adm:
                    hi = max(P['tier'][T[k].tier] for k in rej)
                    lo = min(P['tier'][T[k].tier] for k in adm)
                    if hi > lo:
                        M['tier_sub'] += 1
                        if ttc < P['ttc_safe'] or d_true < 0.45:
                            M['tier_sub_ok'] += 1
                if not adm:
                    continue
                if ranked:
                    adm.sort(key=lambda k: (-mwkr[k], T[k].due, T[k].p))  # Eq. (18)
                else:
                    rng.shuffle(adm)
                pick = adm[0]
                T[pick].assigned = n
                T[pick].started = True
                rb.task = pick
                M['sched'].append(dict(task=pick, robot=n, start=t, end=None,
                                       tier=T[pick].tier))

        # ---------------- execution --------------------------------------
        for n, rb in robots.items():
            if rb.task is None:
                rb.step_pose(rb.base + np.array([0.0, 0.35]), P['dt'])
                continue
            tgt = np.array(T[rb.task].loc)
            rb.step_pose(tgt, P['dt'])
            if np.linalg.norm(rb.ee - tgt) < 0.02:
                T[rb.task].remaining -= P['dt'] * rb.s
                M['busy'][n] += P['dt'] * rb.s

        if all(tk.done for tk in T.values()):
            M['makespan'] = t
            break

        M['s_series'].append((t, robots['R1'].s, robots['R2'].s))
        if len(trace) < 4000:
            trace.append((t, xi.get('R1', 1.0), xi.get('R2', 1.0),
                          robots['R1'].s, robots['R2'].s, d_true))
        t += P['dt']

    if M['makespan'] is None:
        M['makespan'] = duration
    span = M['makespan']
    M['idle_ratio'] = 1.0 - sum(M['busy'].values()) / (len(robots) * span)
    M['trace'] = trace
    M['human_events'] = human.events
    for _k in ('_viol_prev', '_latched_prev', '_zone_prev'):
        M.pop(_k, None)
    return M


# =========================================================================
def run_all(seeds=30, tier_scale=1.0):
    conds = ['FSB', 'FTV', 'VOB', 'PF-Full']
    res = {c: [] for c in conds}
    for c in conds:
        for s in range(seeds):
            res[c].append(simulate(1000 + s, c, tier_scale))
    return res


if __name__ == '__main__':
    import time
    t0 = time.time()
    m = simulate(1000, 'PF-Full')
    print('single run %.1f s wall, makespan %.1f s, violations %d, '
          'latched %d, tier_sub %d, idle %.3f'
          % (time.time() - t0, m['makespan'], m['violations'],
             m['latched'], m['tier_sub'], m['idle_ratio']))
