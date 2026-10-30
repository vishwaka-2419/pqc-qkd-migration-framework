"""Figure 10 -- robustness of the headline results over 20 synthetic topologies.

Four strip-plot panels (a)-(d), one per headline metric of the proposed
scheme: QKD overlay links, physical QKD hops, QKD-backed share of the
QKD-preferred rekeys and the five-year assurance premium.  Every panel shows
the 20 topology seeds of ``results/sensitivity/topology_seeds.csv`` (one 24-h
run per seed with the reference parameters and simulation seed 11) as a box
plot (quartiles, median, whiskers to the extreme values, no separate fliers)
under one dot per seed; the reference topology (seed 7, the one used
throughout the manuscript) is drawn instead as an open diamond at the centre,
on top of everything else.

The dots are spread horizontally so that no dot hides another: each takes
the first of ``N_CAND`` uniform random candidates (``np.random.default_rng(0)``,
the only randomness) that keeps it clear of every dot already placed and of
the reference diamond, measured in printed points.  Nothing but axis labels is
written inside the figure; the numbers for the caption (mean, s.d., range,
quartiles, reference values) are printed by
``python3 -m figures_src.fig10_seeds``.
"""
from __future__ import annotations

import numpy as np
from matplotlib.lines import Line2D

from hybridsim import plotstyle as ps
from figures_src._data import sensitivity

REFERENCE_SEED = 7

# (column in topology_seeds.csv, y label, y limits, y ticks)
PANELS = [
    ("qkd_overlay_links",    "QKD overlay links",        (0, 12),   range(0, 13, 2)),
    ("physical_qkd_hops",    "physical QKD hops",        (0, 22),   range(0, 21, 5)),
    ("qkd_backed_rekey_pct", "QKD-backed rekeys (%)",    (85, 100), range(85, 101, 5)),
    ("premium_npv_kEUR",     "assurance premium (kEUR)", (0, 4600), range(0, 4001, 1000)),
]

# ---------------------------------------------------------------- geometry (in)
WIDTH = 1.0            # fraction of the text width
HEIGHT_IN = 3.0
MARGIN_L_IN = 0.02     # figure edge -> y label of (a)
MARGIN_R_IN = 0.06
GAP_IN = 0.16          # right spine of a panel -> y label of the next panel
TOP_IN = 0.30          # room for the panel letters
BOTTOM_IN = 0.42       # room for the figure-level legend
LEGEND_Y_IN = 0.02     # lower edge of the legend above the figure bottom

# -------------------------------------------------------------------- marks
XLIM = (-0.5, 0.5)     # data units; the single box of every panel sits at x = 0
BOX_W = 0.6            # box width (data units); wider than the dot spread so that
JITTER = 0.20          # the box edges stay visible beside the dots (half-range)
DOT_S = 16.0           # scatter area of a seed dot, pt^2 (4 pt diameter)
REF_S = 56.0           # scatter area of the reference diamond, pt^2
DOT_R_PT = 2.4         # dot radius incl. white edge, used for the spacing
REF_R_PT = 5.8         # diamond half-diagonal incl. edge, used for the spacing
N_CAND = 400           # random candidates tried per dot


# --------------------------------------------------------------------- data
def table():
    """The 20 topology-seed rows, sorted by seed."""
    df = sensitivity("topology_seeds")
    df = df[df["sweep"] == "topology_seed"].sort_values("value").reset_index(drop=True)
    if REFERENCE_SEED not in set(df["value"].astype(int)):
        raise ValueError(f"reference seed {REFERENCE_SEED} is not in topology_seeds.csv")
    return df


def stats() -> list[dict]:
    """Per metric: n, mean, sample s.d., range (with the seeds attaining it),
    quartiles, median and the value of the reference seed."""
    df = table()
    seeds = df["value"].to_numpy(dtype=int)
    out = []
    for col, label, ylim, _ in PANELS:
        v = df[col].to_numpy(dtype=float)
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        ref = float(v[seeds == REFERENCE_SEED][0])
        out.append({
            "column": col, "label": label, "n": int(len(v)),
            "mean": float(v.mean()), "sd": float(v.std(ddof=1)),
            "min": float(v.min()), "max": float(v.max()),
            "seeds_at_min": [int(s) for s in seeds[v == v.min()]],
            "seeds_at_max": [int(s) for s in seeds[v == v.max()]],
            "q1": float(q1), "median": float(med), "q3": float(q3),
            "reference": ref,
            "below_reference": int((v < ref).sum()),
            "equal_reference": int((v == ref).sum()) - 1,
            "above_reference": int((v > ref).sum()),
            "ylim": ylim,
        })
    return out


# ------------------------------------------------------------------ helpers
def _spread(y: np.ndarray, ref: int, sx: float, sy: float, rng) -> np.ndarray:
    """Horizontal offsets (data units) of the dots of one panel.

    ``sx``/``sy`` convert data units to printed points.  The reference seed
    (index ``ref``) sits at x = 0 under its diamond and is an obstacle for the
    others.  The other dots are placed in order of increasing value; each
    takes the first of ``N_CAND`` uniform random candidates in
    [-JITTER, JITTER] that is clear of everything already placed or, if no
    candidate is clear, the candidate with the largest clearance.
    """
    n = len(y)
    x = np.zeros(n)
    px, py, pr = [0.0], [float(y[ref])], [REF_R_PT]
    order = sorted((i for i in range(n) if i != ref), key=lambda i: (y[i], i))
    for i in order:
        cand = rng.uniform(-JITTER, JITTER, N_CAND)
        dist = np.hypot((cand[:, None] - np.array(px)) * sx,
                        (float(y[i]) - np.array(py)) * sy)
        clearance = (dist - (DOT_R_PT + np.array(pr))).min(axis=1)
        ok = np.flatnonzero(clearance >= 0.0)
        k = int(ok[0]) if len(ok) else int(np.argmax(clearance))
        x[i] = cand[k]
        px.append(float(x[i])); py.append(float(y[i])); pr.append(DOT_R_PT)
    return x


def _place(fig, axes) -> None:
    """Position the panels: equal data widths; the y-axis decoration (tick
    labels + y label) of every panel is measured so that the gap between a
    panel's right spine and the next panel's y label is exactly GAP_IN."""
    fig_w, fig_h = fig.get_size_inches()
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    deco = []
    for ax in axes:
        bb = ax.get_window_extent(ren)
        tb = ax.get_tightbbox(ren)
        deco.append((bb.x0 - tb.x0) / fig.dpi)
    panel_w = (fig_w - MARGIN_L_IN - MARGIN_R_IN - sum(deco)
               - (len(axes) - 1) * GAP_IN) / len(axes)
    panel_h = fig_h - TOP_IN - BOTTOM_IN
    x = MARGIN_L_IN
    for ax, d in zip(axes, deco):
        x += d
        ax.set_position([x / fig_w, BOTTOM_IN / fig_h, panel_w / fig_w, panel_h / fig_h])
        x += panel_w + GAP_IN


# --------------------------------------------------------------------- draw
def draw():
    df = table()
    seeds = df["value"].to_numpy(dtype=int)
    ref = int(np.flatnonzero(seeds == REFERENCE_SEED)[0])

    fig = ps.figure(WIDTH, HEIGHT_IN)
    fig_w, fig_h = fig.get_size_inches()
    # provisional, non-overlapping positions; _place() sets the final ones
    axes = [fig.add_axes([0.05 + 0.24 * i, 0.2, 0.15, 0.6]) for i in range(len(PANELS))]
    for ax, (col, label, ylim, ticks) in zip(axes, PANELS):
        ax.set_xlim(*XLIM)
        ax.set_xticks([])
        ax.set_ylim(*ylim)
        ax.set_yticks(list(ticks))
        ax.set_yticklabels([str(t) for t in ticks])
        ax.set_ylabel(label)
    _place(fig, axes)

    rng = np.random.default_rng(0)
    for ax, (col, label, ylim, ticks) in zip(axes, PANELS):
        v = df[col].to_numpy(dtype=float)
        ax.boxplot(v, positions=[0.0], widths=BOX_W, whis=(0, 100), showfliers=False,
                   manage_ticks=False, patch_artist=True, zorder=2,
                   boxprops=dict(facecolor=ps.SURFACE, edgecolor=ps.INK2, linewidth=1.0),
                   medianprops=dict(color=ps.INK, linewidth=1.5),
                   whiskerprops=dict(color=ps.INK2, linewidth=1.0, linestyle="-"),
                   capprops=dict(color=ps.INK2, linewidth=1.0))
        pos = ax.get_position()
        sx = pos.width * fig_w * 72.0 / (XLIM[1] - XLIM[0])
        sy = pos.height * fig_h * 72.0 / (ylim[1] - ylim[0])
        x = _spread(v, ref, sx, sy, rng)
        others = np.arange(len(v)) != ref
        ax.scatter(x[others], v[others], s=DOT_S, marker="o", facecolor=ps.HUE[500],
                   edgecolor=ps.SURFACE, linewidth=0.5, zorder=3,
                   label="one of 20 topology seeds")
        ax.scatter([0.0], [v[ref]], s=REF_S, marker="D", facecolor=ps.SURFACE,
                   edgecolor=ps.INK, linewidth=1.0, zorder=4,
                   label=f"reference seed {REFERENCE_SEED}")

    handles = [
        Line2D([], [], ls="", marker="o", markersize=np.sqrt(DOT_S),
               markerfacecolor=ps.HUE[500], markeredgecolor=ps.SURFACE,
               markeredgewidth=0.5, label="one of 20 topology seeds"),
        Line2D([], [], ls="", marker="D", markersize=np.sqrt(REF_S),
               markerfacecolor=ps.SURFACE, markeredgecolor=ps.INK,
               markeredgewidth=1.0, label=f"reference seed {REFERENCE_SEED}"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, LEGEND_Y_IN / fig_h), ncol=2, frameon=False,
               handlelength=1.4, handletextpad=0.5, columnspacing=2.5,
               borderaxespad=0.0, borderpad=0.0)

    ps.panel_labels(fig, dict(zip("abcd", axes)))
    # one common baseline for the letters (a panel whose top tick label sits
    # at the axes top has a taller tight box than one whose top tick is below)
    letters = [t for t in fig.texts if t.get_gid() == "panel-label"]
    y_top = max(t.get_position()[1] for t in letters)
    for t in letters:
        t.set_position((t.get_position()[0], y_top))
    return fig


# ------------------------------------------------------------- caption numbers
def _print_stats() -> None:
    for st in stats():
        print(f"{st['label']} ({st['column']}), n = {st['n']} topology seeds, "
              f"y axis {st['ylim'][0]}-{st['ylim'][1]}")
        print(f"  mean {st['mean']:.2f}   s.d. (n-1) {st['sd']:.2f}   "
              f"range {st['min']:g}-{st['max']:g} "
              f"(min: seed(s) {st['seeds_at_min']}, max: seed(s) {st['seeds_at_max']})")
        print(f"  quartiles Q1 {st['q1']:.2f}   median {st['median']:.2f}   Q3 {st['q3']:.2f}"
              "   (whiskers: min-max)")
        print(f"  reference seed {REFERENCE_SEED}: {st['reference']:g}  "
              f"({st['below_reference']} seeds below, {st['equal_reference']} equal, "
              f"{st['above_reference']} above)")


if __name__ == "__main__":
    from hybridsim.figcheck import lint
    ps.apply_style()
    _print_stats()
    fig = draw()
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    print("\nlayout (inches from the left edge): y-label left edge .. spines")
    for letter, ax in zip("abcd", fig.axes):
        bb = ax.get_window_extent(ren)
        tb = ax.get_tightbbox(ren)
        print(f"  ({letter}) {tb.x0 / fig.dpi:.3f} .. {bb.x0 / fig.dpi:.3f}-{bb.x1 / fig.dpi:.3f}")
    print("lint:", lint(fig) or "clean")
