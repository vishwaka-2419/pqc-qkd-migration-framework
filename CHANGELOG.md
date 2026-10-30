# Changelog

## v1.1.1 (2026-10-30) — corrections for revision 1 of manuscript QTC-2026-07-0055

Supersedes v1.1.0 as the release cited by the revised manuscript. The
reference-scenario results are unchanged; the corrections affect the
comparison study, the dimensioning table and the portability of the figure
build.

### Fixed
- `hybridsim/simulate.py`: a rekey carried by a fallback mode is counted once
  in `ServiceRun.reactive_fallbacks`. v1.1.0 also incremented the counter when
  the preceding QKD-mode key request failed with a `KMEError`, so scheme D of
  the comparison study reported 26,076 "reactive fallback rekeys" where 8,988
  rekeys (334,080 QKD-preferred minus 325,092 QKD-backed) were carried by a
  fallback mode. `LinkRun.kme_errors` (269 for scheme D) is unchanged and
  counts unsuccessful KME requests at attempt level.
  Regression tests: `tests/test_fallback_counting.py`.
- `run_experiments.py` / `results/pool_dimensioning.csv`: the dimensioning
  check applies the SLA margin of each link's QKD-capable services (gold 2 h
  on the core and DCI links, silver 1 h on the metro links) instead of the
  gold margin everywhere; the metro links now show a re-entry threshold of
  1.5 h and a largest admissible hysteresis factor of 22.6 (columns
  `sla_classes`, `t_min_h` added).
- `figures_src/fig06_cost.py`: hatches are drawn through the edge colour
  instead of the `hatchcolor` property, which needs Matplotlib >= 3.11.

### Added
- `run_sensitivity.py`: two matched-constraint comparison schemes,
  `B_prime_selective_rule_relaxed_constraints` (selective rule under the
  relaxed constraints of scheme B) and
  `F_prime_all_feasible_rule_reference_constraints` (all-feasible rule under
  the reference constraints), 144 scenario runs in total. B' reproduces B and
  F' reproduces F, which attributes the B-F difference to the planning
  constraints rather than to the overlay rule.
- `figures_src/fonts/`: the four TeX Gyre Heros faces (GUST Font License) are
  bundled and registered by `plotstyle.apply_style()`, so the figures and the
  layout lint use the same font metrics in every environment.
- `requirements.txt`: version ranges; the suite is run on Matplotlib 3.10.8
  and 3.11.2 before release (29 tests).

### Changed
- `figures_src/fig07_oat.py`: figure height 6.8 in (was 7.95 in) so that the
  figure and its caption fit one page of the manuscript.

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
