# Reproducibility package

Simulation code and data behind every computational result in the article.
All figures listed below were regenerated from these files and verified
byte-identical to the versions embedded in the manuscript.

## Two simulator versions

The two are identical except for the static task order and the instance
generator. Use the one named against each result; mixing them changes the
fixed-sequence baseline (FSB) by about 1 s of makespan.

| File | Static order | Instance generator | Used for |
|---|---|---|---|
| `dse_sim_results.py` | explicit (T1, T3, T2_0..11, T4_0..11) | twelve-module pack only | Tables 5, 6, 8; Figures 5, 7 |
| `dse_sim_generator.py` | alphabetical | adds `build_tasks_graph` and the PF-Inflate condition | Figure 8; PF-Inflate row of Table 8 |

Both implement Equations (5)-(14) and Algorithms 1-2 at a 10 Hz control
cycle, with lambda = 0.15 as the per-cycle contraction fraction and the
ISO/TS 15066-aligned response-time component of Equation (A1).

## Result-to-script map

| Result | Simulator | Experiment script | Data | Figure script |
|---|---|---|---|---|
| Table 5, Table 6 | `dse_sim_results.py` | `run_conditions.py FSB FTV VOB PF-Full` | `v_*.json` | `paired_stats.py` |
| Table 8 (four ablations) | `dse_sim_results.py` | `run_conditions.py PF-NoFilter PF-CompOnly PF-Static PF-RandTie` | `v_*.json` | `paired_stats.py` |
| Table 8 (PF-Inflate row) | `dse_sim_generator.py` | `run_conditions.py PF-Inflate` | `v_PF-Inflate.json` | `paired_stats.py` |
| Figure 5 | `dse_sim_results.py` | as Table 5 | `v_*.json` | `make_fig5_bars.py` |
| Figure 7 | `dse_sim_results.py` | `frontier.py FSB FTV VOB PF-Full` | `frontier_all.json` | `make_fig7_frontier.py` |
| Figure 8 | `dse_sim_generator.py` | `het.py 0.0 0.15 0.30 0.50 0.70 0.85 1.0` | `het_all.json` | `make_fig8_heterogeneity.py` |
| Figure 4(a) | `dse_sim_results.py` | — | — | `panel_a_feasibility.py` |
| Figure 4(c) | `dse_sim_results.py` | — | — | `panel_c_gantt.py` |
| Figure 9 (appendix support) | `dse_sim_results.py` | tier-scale sweep, `tier_scale` argument | `results_sweep.json` | `make_figs.py` |

Figures 1, 2, 3 and Figure 4(b) are drawn illustrations, not code output.
Figure 6 is a trace plot produced from `M['trace']` of a single replication.

## Reproducing

    pip install numpy scipy matplotlib
    python run_conditions.py PF-Full          # one condition at a time
    python paired_stats.py                    # Tables 5, 6, 8
    python frontier.py FSB FTV VOB PF-Full    # Figure 7 data
    python make_fig7_frontier.py

`run_conditions.py` uses 60 paired replications with common random numbers
(seeds 1000..1059); `frontier.py` uses 12 per point (seeds 1000..1011);
`het.py` uses 20 per point (seeds 2000..2019). Runtime is about 3 s per
replication on one core.

## Scope

Every number is computational. The simulation is planar, with no articulated
kinematics, no rigid-body dynamics and no contact model; occlusion is injected
probabilistically rather than derived from line-of-sight; and the safety-layer
parameters of Table 3 are placeholders pending measurement. Absolute values are
not an industrial benchmark.
