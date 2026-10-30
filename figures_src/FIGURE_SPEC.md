# Figure specification — manuscript QTC-2026-07-0055.R1 (IET Quantum Communication)

Every figure of the manuscript is being redrawn for publication. The author's
instructions, verbatim in substance:

* the previous figures "look AI-like" (pastel multi-colour boxes); use a
  **single-colour (monochrome, one hue) scheme** and a better, more
  professional presentation;
* text must **never overlap** the plot, the data points, other text or a
  neighbouring panel;
* **axis labels and tick labels must be large** (readable at print size);
* figures must **not have titles**; panels are labelled **(a), (b), ...** only,
  in the journal style, and **everything else is said in the caption**.

## 1. Hard rules (checked automatically where possible)

1. **One hue.** Use only `hybridsim.plotstyle` colours: the blue ramp
   `ps.HUE[50..900]`, the ordered `ps.SHADES`, `ps.EMPHASIS`, `ps.MUTED`,
   `ps.SEQ_CMAP`, and the neutrals `ps.INK`, `ps.INK2`, `ps.INK3`, `ps.GRID`,
   `ps.NEUTRAL`. No orange, green, red, yellow, magenta, violet anywhere.
   Different series are told apart by **shade + line style (`ps.LINESTYLES`)
   + marker (`ps.MARKERS`) + hatch (`ps.HATCHES`)**, never by shade alone, so
   the figure also reads in greyscale.
2. **No titles.** Never call `set_title`, `suptitle`, or write a heading-like
   text above a panel. Panel letters come from `ps.panel_labels(fig, {...})`
   (bold "(a)" at the top-left of each panel). A single-panel figure gets no
   letter. Series names, protocol names, parameter names etc. go into axis
   labels, legends or direct labels — never into a title.
3. **Sizes.** Draw at the final printed width with `ps.figure(width, height)`:
   `width` is a fraction of the manuscript text width (`ps.FULL` = 160 mm);
   use 1.0 unless the spec says otherwise. Do not change the rcParams font
   sizes: axis labels 10 pt, ticks/legend 9 pt, annotations `ps.SIZE_ANNOT`
   (8.5 pt). The lint rejects any text below 8 pt. Figures taller than 8.5 in
   are not allowed (page height).
4. **No overlaps.** `hybridsim.figcheck.lint(fig)` must return an empty list.
   It flags text–text, text–data, legend–data, text–bar and text-spilling-into
   -another-panel collisions, and any title. Intentional placements (a value
   printed inside a heat-map cell or inside a wide bar) must be declared with
   `gid="allow-overlap"` on that artist — use this only where the text is
   genuinely legible on top of the artist, never to silence a real collision.
5. **Text colour is ink.** Labels, values and annotations are `ps.INK` /
   `ps.INK2` / `ps.INK3`; a coloured mark next to them carries identity.
   White text is allowed only inside dark heat-map cells (`gid="allow-overlap"`).
6. **Fonts.** The rcParams already select TeX Gyre Heros (Helvetica clone)
   with mathtext in the same face; just write `$R_{\min}$`, `$\beta$`,
   `$\kappa$` etc. Do not change `font.*` or `mathtext.*`.
7. **Grid.** Light horizontal grid only (`axes.grid.axis = y`); for horizontal
   bar charts switch to `ax.grid(axis="x"); ax.grid(False, axis="y")`.
8. **Numbers in the figure are the model's numbers.** Load data only through
   `figures_src._data` (`reference()`, `sensitivity(name)`) or the `hybridsim`
   package; never type a result by hand.
9. **Whitespace.** Use `fig.tight_layout(...)` or `fig.subplots_adjust(...)`
   so that nothing is cut and panels do not touch. Legends go in empty
   regions of the data area or outside the axes (`bbox_to_anchor`), never over
   data.
10. **Reproducibility.** The module must be importable as
    `figures_src.figNN_name` and expose `draw() -> Figure`. No file I/O in
    `draw()` other than reading the data sources above. No randomness other
    than `np.random.default_rng(0)` for jitter.

## 2. Workflow for a figure module

```
cd /home/user/work/v2
python3 build_figures.py 4            # builds figures/Figure_4.{png,pdf,tiff}; fails on lint issues
cat figures/lint/Figure_4.txt         # the lint report
```
Then **look at the PNG** (`figures/Figure_4.png`) with the image viewer, and
also crop it into halves/quadrants at full resolution (PIL) to check small
details: label collisions, clipped text, legibility, consistent alignment,
panel letters present and at the top-left corner, nothing cut at the edges.
Iterate until (i) the lint is empty and (ii) you would accept it in a journal.
Use `python3 build_figures.py 4 --lenient` only while iterating.

Write the caption to `figures_src/captions/Figure_N.tex` (LaTeX body only, no
`\caption{}`; see §4). Write nothing else outside your module and caption file.

## 3. Palette reference

| name | hex | use |
|---|---|---|
| `HUE[900]` | #0b2240 | darkest; emphasis lines |
| `HUE[800]` | #14365f | `EMPHASIS`, first series |
| `HUE[500]` | #3576bd | second series |
| `HUE[300]` | #86afdb | third series |
| `HUE[200]` | #b2cbe8 | `MUTED` (comparison bars) |
| `HUE[100]` | #d6e3f3 | fourth series / light fills |
| `HUE[50]`  | #edf3fa | background tint of highlighted boxes |
| `NEUTRAL`  | #c9c9c9 | "rejected / not applicable" fills |
| `INK3` dotted/dashed | #7c7c7c | reference lines (thresholds, limits) |

Sequential magnitude: `ps.SEQ_CMAP` (HUE 50 → 900). Shaded time windows
(`axvspan`): `HUE[100]` with `alpha=0.5`, `lw=0`.

## 4. Captions (journal style)

Each caption is self-contained: a reader must understand the figure without the
text. Structure: one lead sentence saying what the figure shows; then one
clause per panel "(a) ...; (b) ..."; then what every line style, marker, hatch,
shaded region and reference line means, with the symbols used in the paper
(`$R_{\min}$`, `$\beta B_{\max}$`, `$\kappa$`, `$T_{\min}$`); then the
provenance sentence (seeded synthetic scenario, topology seed 7, simulation
seed 11, planning-model outputs, no carrier data) where relevant. Keep the
scientific content of the previous caption (`captions/_current_captions.tex`)
and the manuscript's cross-references (`Eq.~\eqref{eq:reserve}`,
`Eq.~\eqref{eq:dimensioning}`, `Table~\ref{tab:costsplit}`,
`Table~\ref{tab:baselines}`) where they appear there. Numbers quoted in a
caption must be the numbers the module plots. Do not start with "Figure N:"
(LaTeX adds it). Use `\rev{...}` nowhere — the integrator marks the change.

## 5. Per-figure specification

Widths are fractions of the text width. Heights are suggestions.

### Figure 2 — `fig02_envelope.py` (width 1.0, ~3.4 in) — two panels (a), (b)
Data: `ref = reference()`; `ref.links` (kinds `dci`, `metro`, `core`, others);
`plan_qkd_link(link.distance_km, link.qkd_resources)`; envelope
`skr_point_to_point(d)` for d = 1..230 km (0 below `R_min`, so plot NaN there);
`DEFAULT.r_min_bps` = 100, `DEFAULT.max_hop_km` = 80.
(a) semilog-y envelope (dark line) vs span length; horizontal dotted
reference at `R_min` and vertical dashed reference at 80 km, each with a short
text label placed where nothing else is (e.g. the 80 km label near the top of
the line, the `R_min` label just above the dotted line at the far left where
the envelope is still high); operating points of qualified routes at their
per-hop length and per-hop rate: DCI direct spans (circle, HUE[800]), metro
direct spans (square, HUE[500]), core trusted-node routes (triangle,
HUE[300]), white edge; annotate the two core routes with "core-0: 5 × 66 km"
style labels using leader lines, placed in free space to the right of the
points; legend in the empty upper-right region. Skip metro links without a
dedicated optical path, as the old code did.
(b) horizontal bars of route length for the six core routes sorted by length;
qualified = HUE[800], rejected = NEUTRAL with hatch "////"; the per-route
annotation (e.g. "6 hops · exceeds trusted-node limit", "5 hops · qualified")
right of the bar, in INK2, within the axes (extend xlim so that the longest
text fits; shorten the reasons: "trusted-node limit exceeded", "approved sites
insufficient", "no qualified optical path", "qualified"); y tick labels are the
link ids; legend for the two fills in free space (or explain in the caption and
omit the legend). Nothing may leave the panel.

### Figure 3 — `fig03_mode_mix.py` (width 0.8, ~3.0 in) — single panel, no letter
Data: `ref.mix2`, `ref.mix3` (dict mode -> services), `hybridsim.modes.ALL_MODES`.
Grouped horizontal bars per mode (modes with any count), Phase 2 "PQC
migration baseline" = MUTED with hatch "////", Phase 3 "selective QKD overlay"
= EMPHASIS; value at the end of each bar (INK2); x axis "services (of 60)";
y tick labels `ps.MODE_LABELS`; legend in the empty lower-right region; order
modes top-to-bottom Traditional only, PQC only, PQ/T hybrid, QKD-assisted,
PQ/T + QKD.

### Figure 4 — `fig04_pool.py` (width 1.0, ~5.0 in) — two stacked panels (a), (b), shared x
Data: `ref.result.link_runs` (each `lr.link.link_id`, `lr.pool_trace` = list of
(t_s, level_bits, reserve_h)); `ref.trace_ids` = ('dci-0', 'core-0', 'dci-1');
`ref.outages` = {'dci-0': (32400, 54000), 'core-0': (7200, 18000)} seconds;
pool capacity 5.12 Mbit; `DEFAULT.protected_fraction` = 0.05;
`MIN_RESERVE_S['gold']` = 7200 s; `DEFAULT.reentry_multiplier` = 1.5.
Series styles: dci-0 solid HUE[800]; core-0 dashed HUE[500]; dci-1 dotted
HUE[300] (same style in both panels; one legend only, in (a), in the empty
region at the right of the panel, between the top line and the reserve line —
or outside the axes to the right).
(a) pool level (Mbit) vs time of day (h, 0–24, ticks every 3 h); outage
windows as light shaded spans (HUE[100], alpha 0.5) labelled "dci-0 refill
outage" / "core-0 refill outage" **above** the data (set ylim to ~6.3 so there
is room above 5.12 Mbit); the protected reserve `βB_max` as a dotted INK3 line
with a short label in free space.
(b) predicted reserve time (h): show the full range (core-0 sits at ~13 h), so
set ylim 0–14.5 instead of clipping; the gold demotion margin (2 h, dashed
INK3) and the re-entry threshold (3 h, dotted INK3) each with a short text
label placed in free space (e.g. right end, between the lines, or outside the
axes at x > 24 with `clip_on=False`, making room with `subplots_adjust`).
Caption: dci-0 outage 09:00–15:00 triggers reserve-time demotion when the
signal reaches the 2 h margin and re-entry only above 3 h (`κ = 1.5`);
core-0 outage 02:00–05:00 does not, its reserve stays above the margin.

### Figure 5 — `fig05_latency.py` (width 1.0, ~2.8 in) — three panels (a) IKEv2/IPsec, (b) MACsec, (c) OTN
Data: `ref.result.service_runs` (`sr.service.protocol`, `sr.latency_samples_ms`,
`sr.service.latency_budget_ms`).
Empirical CDF per protocol (one dark line each, HUE[800]); the configured
latency budgets as dotted INK3 vertical lines, each labelled with its value
("8 ms") near the top, no two labels touching; use a **logarithmic x axis**
(e.g. 0.5–60 ms) so the budgets 8/14/22/50 ms and the data (1–10 ms) are both
readable; x label "sampled rekey-control latency (ms)"; y label "empirical
CDF" on the left panel only (shared y). Identify the protocol by a legend entry
inside each panel ("IKEv2/IPsec, n = 1234 samples") in the empty lower-right
region, not by a title. p50/p99 values go to the caption (compute them in the
module and print them when run as a script so they can be copied).

### Figure 6 — `fig06_cost.py` (width 1.0, ~4.6 in) — three panels
Data: `five_year_tco(ref.links, ...)`: `t['breakdown']` = list of (scope
'shared'|'incremental', kind 'capex'|'opex', item name, npv kEUR), 12 items;
`t['pqc_only_npv'][-1]` = 1100.6, `t['hybrid_npv'][-1]` = 3939.2,
`t['premium_npv']` = 2838.6; `five_year_tco(links, qkd_pair_capex=c)` for
c = 20..140; `five_year_tco(links, horizon_years=h, discount_rate=r)`.
Layout: (a) occupies the left ~45 % at full height; (b) top right, (c) bottom
right (use `fig.add_gridspec`).
(a) itemised five-year NPV: one horizontal bar per cost item (12 rows), grouped
"shared by both strategies" (5 items, MUTED) above "incremental to the
selective overlay" (7 items, EMPHASIS), with hatch "////" for opex items and
plain for capex; item names as y tick labels (shorten: "Policy platform",
"PQC integration", "Programme, phases 1–2", "Platform operations", "PQC
operations", "QKD endpoint pairs (13 hops)", "Trusted-site construction",
"QKD service integration", "Optical engineering", "Programme, phase 3",
"QKD operations", "Trusted-site operations"); value (kEUR, 0 decimals) at the
end of each bar; group totals written once per group ("shared 1 100.6 kEUR",
"incremental 2 838.6 kEUR") in free space inside the panel; x label
"five-year NPV (kEUR)"; a legend for the two fills and the hatch.
(b) five-year NPV cost vs QKD endpoint-pair capex per physical hop (20–140
kEUR): "PQC migration baseline" (dashed HUE[500]) and "PQC + selective QKD"
(solid HUE[800]); the gap filled HUE[100] alpha 0.5 and labelled "assurance
premium" in the middle of the gap; reference capex 100 kEUR as a dotted INK3
vertical line; legend in free space (upper left is free? check) .
(c) assurance premium NPV (kEUR) vs discount rate (0–10 %) for horizons 5, 7
and 10 years: three lines with `SHADES[0..2]`, `LINESTYLES[0..2]`,
`MARKERS[0..2]`; legend in free space (lower left).

### Figure 7 — `fig07_oat.py` (width 1.0, ~7.6 in) — 6 rows × 3 columns, letters (a)–(f) one per row
Data: `sensitivity('oat_sweeps')` columns `parameter`, `value`,
`physical_qkd_hops`, `qkd_backed_rekey_pct`, `min_pool_fraction`.
Rows = parameters in this order with these x-axis labels: `max_hop_km`
"designed hop limit (km)", `trusted_node_limit` "trusted-node policy limit",
`r_min_bps` "planning floor $R_{\min}$ (bit/s)", `protected_fraction`
"protected fraction $\beta$", `reentry_multiplier` "re-entry hysteresis
$\kappa$", `reserve_margin_scale` "reserve-margin scale". Columns = metrics
with y labels "physical QKD hops" (ylim 0–22), "QKD-backed rekeys (%)" (ylim
0–100), "minimum pool level (fraction)" (ylim 0–0.7). Values are swept at
discrete points: plot them at **equally spaced categorical positions** with the
actual values as tick labels (format 1e3 as "1k", 1e5 as "100k"), as a line
with markers (HUE[800], marker "o", white edge); the reference value (80, 4,
100, 0.05, 1.5, 1.0) drawn as a larger open marker ring (INK) and explained in
the caption; no per-point value labels. Letters (a)–(f) at the left of each
row: pass `{letter: [ax_row...]}` to `panel_labels` so the letter sits at the
top-left of the whole row. Keep the row height ~1.1 in. All tick labels must
be present and non-overlapping in every panel.

### Figure 8 — `fig08_grid.py` (width 1.0, ~3.6 in) — two panels (a), (b)
Data: `sensitivity('hop_limit_grid')`; `value` is "hop|limit"; metrics
`physical_qkd_hops`, `qkd_overlay_links`, `premium_npv_kEUR`.
(a) heat map of physical QKD hops (SEQ_CMAP, vmin 0) over designed hop limit
(rows: 50, 60, 70, 80, 90, 100, 120 km) × trusted-node policy limit
(columns: 0, 1, 2, 3, 4, 5, 6, 8); each cell prints "hops" and, on a second
line, "(links)"; (b) heat map of the five-year assurance premium (MEUR, one
decimal). Cell text in INK on light cells and white on dark cells
(`gid="allow-overlap"`), reference cell (80 km, 4) outlined in INK 1.4 pt;
colour bars with axis labels "physical QKD hops" / "assurance premium (MEUR)";
x label "trusted-node policy limit", y label "designed hop limit (km)".

### Figure 9 — `fig09_baselines.py` (width 1.0, ~3.6 in) — five panels (a)–(e), shared y
Data: `sensitivity('baselines')`; rows A–F in `parameter`; columns
`qkd_backed_rekey_pct`, `physical_qkd_hops`, `trusted_sites`,
`min_pool_fraction`, `kme_errors`, `reactive_fallback_rekeys`,
`premium_npv_kEUR`.
Scheme labels (y tick labels on the left panel only, top to bottom):
"A  PQC/PQ-T only, no QKD", "B  QKD on every feasible link", "C  selective,
static 20 % pool gate", "D  selective, reactive fallback only", "E  selective,
no re-entry hysteresis", "F  proposed (selective, reserve-time, hysteresis)".
Horizontal bars, F = EMPHASIS, A–E = MUTED. Panels with x labels:
(a) "QKD-backed share of QKD-preferred rekeys (%)" → "QKD-backed rekeys (%)",
(b) "physical QKD hops", (c) "minimum pool level (fraction)", (d) "hard KME
starvation events", (e) "five-year assurance premium (MEUR)". Value labels at
the bar end (for (b) append the trusted sites in brackets, for (d) append the
reactive fallbacks in brackets, e.g. "269 (26 076)"); set each xlim so that
the longest label fits inside the panel (≈ 1.6 × max value); zero-valued rows
print "0" just right of the axis. Letters via `panel_labels`.

### Figure 10 — `fig10_seeds.py` (width 1.0, ~3.0 in) — four panels (a)–(d)
Data: `sensitivity('topology_seeds')`; 20 rows (`value` = seed), reference
seed 7; columns `qkd_overlay_links`, `physical_qkd_hops`,
`qkd_backed_rekey_pct`, `premium_npv_kEUR`.
Each panel: box plot (INK2 lines, median INK, no fliers) plus jittered points
(HUE[500], white edge, `default_rng(0)`), the reference seed as a larger open
diamond (INK edge, white face) drawn on top; y label names the metric ("QKD
overlay links", "physical QKD hops", "QKD-backed rekeys (%)", "assurance
premium (kEUR)"); no x ticks; ylim with headroom (links 0–12, hops 0–22, %
85–100, kEUR 0–4600). One figure-level legend below the panels ("one of 20
topology seeds", "reference seed 7"). Mean, s.d. and range go into the
caption (print them when run as a script).

### Figure 1 — `fig01_architecture.tex` (TikZ, standalone; printed width 160 mm)
A clean engineering block diagram of the framework, in the style of a
systems/network architecture figure (thin dark-blue outlines `h800`, white
fills, one tinted fill `h50` for the policy engine, Helvetica (tgheros),
9 pt body / 8 pt detail text, `Stealth` arrows). Content, top to bottom, as
four horizontal tiers of boxes:

1. **Service inventory and context** — one box listing per-service inputs:
   secrecy lifetime, migration lead time, planning horizon (Mosca margin),
   SLA class, capability set, HNDL exposure, fail-closed flag.
2. **Crypto-agile policy engine** (tinted) — four sub-boxes side by side:
   "Mosca prioritisation" → "admissible-mode selection (Traditional → PQC →
   PQ/T hybrid → QKD-assisted → PQ/T + QKD)" → "reserve-time forecast and
   hysteresis (κ)" → "fail-closed downgrade rules"; plus one box "selective
   overlay planning: route qualification (hop limit, trusted-node limit,
   $R_{\min}$)" attached to the tier.
3. **Key sources** — two boxes: "PQ/T hybrid key establishment (ML-KEM +
   ECDH)" and "paired KME pool (key IDs, single use, protected reserve
   βB_max)" fed from a small box "QKD links (direct spans, trusted-node
   routes)".
4. **Protocol adapters / binding profiles** — three boxes: "IKEv2 (RFC 9370
   additional key exchanges, RFC 9867 PPK)", "MACsec/MKA (abstraction)", "OTN
   encryptor (abstraction)"; below them a tier **Encrypted carrier services**:
   "IPsec tunnels", "Ethernet secure associations", "optical channels".

Arrows: downward from tier 1 to 2 ("service context"), 2 to 3 ("mode decision,
key requests"), 3 to 4 ("keys, key IDs"), 4 to services ("rekey"); one
upward return path on the right edge labelled "telemetry: pool level, reserve
time, outages, rekey outcomes" from tiers 3–4 back to tier 2. Mark the
boundary of what the simulator implements with a dashed rounded rectangle
labelled "scope of the reference implementation (seeded synthetic scenario;
no carrier data)". No panel letters needed (one diagram), no title. Compile
with `python3 build_figures.py 1`; iterate until the PNG looks like a
publication-quality architecture figure: aligned boxes, equal margins, no
text touching borders, nothing overflowing.

Caption must describe each tier, the arrow semantics, the dashed scope
boundary and the "no carrier data" statement (see the current caption).

### Graphical abstract — `graphical_abstract.tex` (TikZ, standalone; exactly 50 mm wide × 60 mm high)
Same style as Figure 1, drastically simplified: three stacked boxes with
downward arrows ("Service context: lifetime · capability · SLA · route ·
threat" → "Crypto-agile policy: Mosca margin · reserve-time forecast ·
fail-closed rules" → "Admissible protection: PQ/T baseline · selective QKD")
and a bottom results box "Seeded synthetic scenario: 6 of 35 links receive QKD
· 13 physical hops, 7 trusted sites · 94.2 % of QKD-preferred rekeys
QKD-backed · 2.84 MEUR assurance premium (5-year NPV)" and the footer
"planning-model outputs, not carrier measurements". Text 6–7 pt, nothing
smaller than 5.5 pt. Set the page size to exactly 50 mm × 60 mm with
`\documentclass[tikz]{standalone}` plus a fixed-size clip, or draw on a
50 × 60 mm canvas with `\useasboundingbox`.
