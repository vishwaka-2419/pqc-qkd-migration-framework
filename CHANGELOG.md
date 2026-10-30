# Changelog

## v1.1.0 (2026-10-29) — revision 1 of manuscript QTC-2026-07-0055

Added for the revised manuscript. The defaults reproduce every v1.0.0 number
exactly (`tests/test_revision.py::test_defaults_reproduce_v1_0_0_headline_metrics`).

### Model
- `hybridsim/params.py`: `PlanningParams` collects every previously hard-coded
  planning constant (hop limit, trusted-node limit, rate floor, protected
  fraction, re-entry hysteresis, SLA-margin scale) plus the gating rule and the
  overlay-selection rule used by the comparison baselines.
- `hybridsim/kms.py`: `PairedKMEPool.max_reserve_time_s` implements the
  dimensioning bound `(1 - beta) * B_max / C_l >= kappa * T_min`.
- `hybridsim/simulate.py`: records mode transitions, hard KME errors, minimum
  pool level and downgraded rekeys of HNDL-exposed services; supports
  `reserve_time`, `static_threshold` and `reactive_only` gating.
- `hybridsim/selection.py`: `selective`, `all_feasible` and `none` overlay rules.
- `hybridsim/tco.py`: configurable horizon and discount rate; itemised
  shared-vs-incremental breakdown; phase-3 programme charged only when a route
  is overlaid.
- `hybridsim/experiments.py`: single scenario runner shared by all scripts.

### Experiments
- `run_sensitivity.py`: one-at-a-time sweeps, hop-limit x trusted-node grid,
  six comparison schemes (A-F), 20 topology seeds, 20 simulation seeds,
  fail-closed vs fail-open negative control, cost horizon/discount sweep and
  cost breakdown (142 scenario runs, ~3 min on 4 cores).
- `make_figures.py`: Figures 7-10.
- `results/pool_dimensioning.csv`: per-link dimensioning check.

### Figures
- All ten figures and the graphical abstract redrawn for publication: one
  module per figure in `figures_src/`, a single-hue palette with line styles,
  markers and hatching carrying identity (`hybridsim/plotstyle.py`), no
  in-figure titles (panel letters only; everything else is in the captions),
  10-pt axis labels at the printed width, Figure 1 and the graphical abstract
  as TikZ block diagrams, output as 600-dpi PNG, LZW TIFF and vector PDF.
- `build_figures.py` builds any figure and fails if the layout lint
  (`hybridsim/figcheck.py`: titles, overlapping text, small text) reports an
  issue; `tests/test_figures.py` runs the lint over every matplotlib figure.
- Figure 2, 4, 5 and 6 gained panels; Figure 7 is a 6 x 3 grid of
  parameter sweeps; Figure 9 compares the six schemes on five metrics.

### Housekeeping
- `__pycache__` removed from version control; package version set to 1.1.0.

## v1.0.0 (2026-07-18)

Version used for the originally submitted manuscript
(Zenodo DOI 10.5281/zenodo.21427006).
