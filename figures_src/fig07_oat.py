"""Figure 7 -- one-at-a-time sensitivity of the selective QKD overlay to the
six planning parameters.

Six rows (a)-(f), one per swept parameter, times three columns, one per
metric (physical QKD hops, QKD-backed share of the QKD-preferred rekeys,
minimum pool level during the 24-h run).  Every panel draws the swept values
at equally spaced categorical positions as one dark line with markers; the
reference configuration (``hybridsim.params.DEFAULT``) is marked by a larger
open ring.  No value labels, no titles: the metric names are one rotated
label per column, the parameter names one x label per row (under the middle
panel), and everything else is said in ``captions/Figure_7.tex``.

Data: ``results/sensitivity/oat_sweeps.csv`` through
``figures_src._data.sensitivity('oat_sweeps')`` (one 24-h run per swept
value, all other parameters at their reference values).

The layout is measured, not guessed.  Horizontally, the widths of the y tick
labels and of the rotated column labels come from the renderer and the x
limits of every row are chosen so that its outermost tick labels end inside
the panel; a row whose neighbouring x tick labels would come closer than
``STAGGER_MIN_GAP_PT`` (seven three-digit labels do not fit side by side in a
1.6-in panel at 9 pt) alternates its tick labels between two lines.
Vertically, the gap below a row holds, in this order, its x tick labels, its
x label and the panel letter of the next row, each in its own band, so that
a letter can never be read as belonging to the x label above it.  Run
``python3 -m figures_src.fig07_oat`` to print the plotted numbers, the
geometry (tick-label gaps, band clearances) and the lint result.
"""
from __future__ import annotations

import numpy as np

from hybridsim import plotstyle as ps
from figures_src._data import sensitivity, DEFAULT

# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------


def _fmt(v: float) -> str:
    """Tick label of a swept value: 0.05 -> '0.05', 1e3 -> '1k', 1e5 -> '100k'."""
    return f"{v / 1e3:g}k" if v >= 1e3 else f"{v:g}"


# (parameter column in oat_sweeps.csv, x label of the row)
ROWS = [
    ("max_hop_km",           "designed hop limit (km)"),
    ("trusted_node_limit",   "trusted-node policy limit"),
    ("r_min_bps",            "planning floor $R_{\\min}$ (bit/s)"),
    ("protected_fraction",   "protected fraction $\\beta$"),
    ("reentry_multiplier",   "re-entry hysteresis $\\kappa$"),
    ("reserve_margin_scale", "reserve-margin scale"),
]
LETTERS = "abcdef"

# (metric column, rotated column label, y limits, y ticks, y tick labels);
# every column has about 10 % headroom above its last tick so that the top
# tick label stays inside the panel and the markers are never cut
COLS = [
    ("physical_qkd_hops",    "physical QKD hops",             (0.0, 22.0),  [0, 10, 20],   ["0", "10", "20"]),
    ("qkd_backed_rekey_pct", "QKD-backed rekeys (%)",         (0.0, 110.0), [0, 50, 100],  ["0", "50", "100"]),
    ("min_pool_fraction",    "minimum pool level (fraction)", (0.0, 0.7),   [0, 0.3, 0.6], ["0", "0.3", "0.6"]),
]

# --------------------------------------------------------------------------
# geometry (inches unless stated otherwise)
# --------------------------------------------------------------------------
HEIGHT_IN = 6.8
MARGIN_V_IN = 0.03        # above the letter "(a)" and below the last x label
LEFT_IN = 0.02
RIGHT_IN = 0.05
YLABEL_GAP_IN = 0.045     # rotated column label -> y tick labels
LETTER_CLEAR_IN = 0.07    # column label of column 1 -> panel letters (horizontal)
COL_CLEAR_IN = 0.07       # right edge of a panel -> column label of the next
BAND_CLEAR_IN = 0.035     # x label of a row -> panel letter of the next row (vertical)
XLABEL_PAD_PT = 2.5
LETTER_PAD_PT = 2.0       # same as ps.panel_labels default
MARKER_CLEAR_IN = 0.085   # outermost marker centre -> y spine
END_OVERHANG_IN = 0.012   # an end tick label may protrude this far beyond the panel
STAGGER_MIN_GAP_PT = 3.5  # neighbouring x tick labels closer than this -> two lines
STAGGER_DROP_PT = 10.0    # extra pad of the lower line of x tick labels

LINE_W = 1.3
MARKER_PT = 5.0
RING_PT = 10.0


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def table() -> dict:
    """{parameter: DataFrame sorted by value; attrs 'ref', 'i_ref'}."""
    df = sensitivity("oat_sweeps")
    out = {}
    for param, _ in ROWS:
        sub = df[df["parameter"] == param].copy()
        if sub.empty:
            raise ValueError(f"no rows for parameter {param!r} in oat_sweeps.csv")
        sub["value"] = sub["value"].astype(float)
        sub = sub.sort_values("value").reset_index(drop=True)
        ref = float(getattr(DEFAULT, param))
        i_ref = int(np.argmin(np.abs(sub["value"].to_numpy() - ref)))
        if abs(sub["value"].iloc[i_ref] - ref) > 1e-9 * max(1.0, abs(ref)):
            raise ValueError(f"reference value {ref} of {param} is not in the sweep")
        sub.attrs["i_ref"] = i_ref
        sub.attrs["ref"] = ref
        out[param] = sub
    return out


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _extent(fig, ren, s: str, size: float, rotation: float = 0.0, weight: str = "normal"):
    """(width, height) in inches of a string rendered in the figure's font."""
    t = fig.text(0, 0, s, fontsize=size, rotation=rotation, fontweight=weight)
    bb = t.get_window_extent(ren)
    t.remove()
    return bb.width / fig.dpi, bb.height / fig.dpi


def _row_padding(width_in: float, label_w: list[float]) -> float:
    """Categorical padding p (in slots): the n points sit at 0..n-1 with x
    limits (-p, n-1+p), chosen so that the outermost tick labels end inside
    the panel (up to END_OVERHANG_IN) and the outermost markers keep
    MARKER_CLEAR_IN from the y spine."""
    n = len(label_w)
    need = max(MARKER_CLEAR_IN,
               0.5 * label_w[0] - END_OVERHANG_IN,
               0.5 * label_w[-1] - END_OVERHANG_IN)
    slot = (width_in - 2.0 * need) / (n - 1)
    return need / slot


def _min_gap_pt(width_in: float, pad: float, label_w: list[float]) -> float:
    """Smallest gap between neighbouring (single-line) x tick labels, points."""
    n = len(label_w)
    slot = width_in / (n - 1 + 2 * pad)
    return 72.0 * min(slot - 0.5 * (a + b) for a, b in zip(label_w[:-1], label_w[1:]))


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def draw():
    data = table()

    fig = ps.figure(1.0, HEIGHT_IN)
    W, H = fig.get_size_inches()
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    pt = 1.0 / 72.0
    rc = ps.plt.rcParams
    ytick_lead = (rc["ytick.major.size"] + rc["ytick.major.pad"]) * pt
    xtick_lead = (rc["xtick.major.size"] + rc["xtick.major.pad"]) * pt

    # ---- measured text sizes ----------------------------------------------
    ytick_w = [max(_extent(fig, ren, s, ps.SIZE_TICK)[0] for s in labels)
               for *_, labels in COLS]
    ylabel_w = max(_extent(fig, ren, lab, ps.SIZE_LABEL, rotation=90)[0]
                   for _, lab, *_ in COLS)
    tick_h = _extent(fig, ren, "0123456789.k", ps.SIZE_TICK)[1]
    letter_h = _extent(fig, ren, "(a)", ps.SIZE_PANEL, weight="bold")[1]

    # ---- columns -----------------------------------------------------------
    # column 1: [margin][column label][clearance for the panel letters][y ticks]
    # columns 2, 3: [clearance][column label][gap][y ticks]
    lead = [LEFT_IN + ylabel_w + LETTER_CLEAR_IN + LETTER_PAD_PT * pt + ytick_w[0] + ytick_lead]
    for j in (1, 2):
        lead.append(COL_CLEAR_IN + ylabel_w + YLABEL_GAP_IN + ytick_w[j] + ytick_lead)
    panel_w = (W - RIGHT_IN - sum(lead)) / 3.0
    x_left, x = [], 0.0
    for j in range(3):
        x += lead[j]
        x_left.append(x)
        x += panel_w

    # ---- rows: tick labels, categorical padding, two-line rows -------------
    rows = []
    for param, xlabel in ROWS:
        sub = data[param]
        labels = [_fmt(v) for v in sub["value"]]
        label_w = [_extent(fig, ren, s, ps.SIZE_TICK)[0] for s in labels]
        pad = _row_padding(panel_w, label_w)
        gap = _min_gap_pt(panel_w, pad, label_w)
        stagger = gap < STAGGER_MIN_GAP_PT
        # space below the axes: x tick labels (one or two lines) and the x label
        below = (xtick_lead + tick_h + (STAGGER_DROP_PT * pt if stagger else 0.0)
                 + XLABEL_PAD_PT * pt + _extent(fig, ren, xlabel, ps.SIZE_LABEL)[1])
        rows.append(dict(param=param, xlabel=xlabel, sub=sub, labels=labels,
                         pad=pad, gap_pt=gap, stagger=stagger, below=below))

    # ---- vertical bands ----------------------------------------------------
    # The top tick label of a column may protrude above the axes by up to
    # half its height minus the headroom above the last tick; the letter of
    # a row sits above that.  The protrusion depends on the axes height, so
    # iterate (it converges at once).
    letter_band = LETTER_PAD_PT * pt + letter_h
    ax_h, overhang = 1.0, 0.0
    for _ in range(3):
        top = MARGIN_V_IN + letter_band + overhang
        gaps = [row["below"] + BAND_CLEAR_IN + letter_band + overhang for row in rows[:-1]]
        bottom = rows[-1]["below"] + MARGIN_V_IN
        ax_h = (H - top - sum(gaps) - bottom) / 6.0
        overhang = max(0.0, max(0.5 * tick_h - (1.0 - yticks[-1] / ylim[1]) * ax_h
                                for _, _, ylim, yticks, _ in COLS))
    y_bottom, y = [], H - top
    for r in range(6):
        y -= ax_h
        y_bottom.append(y)
        if r < 5:
            y -= gaps[r]

    axes = [[fig.add_axes([x_left[j] / W, y_bottom[r] / H, panel_w / W, ax_h / H])
             for j in range(3)] for r in range(6)]

    # ---- content -----------------------------------------------------------
    for r, row in enumerate(rows):
        sub, n = row["sub"], len(row["sub"])
        xs = np.arange(n)
        i_ref = sub.attrs["i_ref"]
        for j, (col, _, ylim, yticks, ytlabels) in enumerate(COLS):
            ax = axes[r][j]
            vals = sub[col].to_numpy(dtype=float)
            ax.plot(xs, vals, color=ps.HUE[800], lw=LINE_W, ls="-",
                    marker="o", ms=MARKER_PT, mfc=ps.HUE[800], mec="white", mew=0.7,
                    clip_on=False, zorder=3, label=col)
            ax.plot([xs[i_ref]], [vals[i_ref]], ls="none", marker="o", ms=RING_PT,
                    mfc="none", mec=ps.INK, mew=0.9, clip_on=False, zorder=4,
                    label="reference")
            ax.set_xlim(-row["pad"], n - 1 + row["pad"])
            ax.set_xticks(xs)
            ax.set_xticklabels(row["labels"])
            ax.set_ylim(*ylim)
            ax.set_yticks(yticks)
            ax.set_yticklabels(ytlabels)
            if row["stagger"]:
                # every second tick label one line lower (tick marks unchanged)
                for i, tick in enumerate(ax.xaxis.get_major_ticks()):
                    if i % 2:
                        tick.set_pad(rc["xtick.major.pad"] + STAGGER_DROP_PT)
            if j == 1:
                ax.set_xlabel(row["xlabel"], labelpad=XLABEL_PAD_PT)

    # ---- one rotated label per column, centred on the column ---------------
    y_centre = 0.5 * (y_bottom[0] + ax_h + y_bottom[-1])
    for j, (_, ylabel, *_) in enumerate(COLS):
        x_right = x_left[j] - ytick_lead - ytick_w[j] - (
            YLABEL_GAP_IN if j else LETTER_CLEAR_IN + LETTER_PAD_PT * pt)
        fig.text(x_right / W, y_centre / H, ylabel, rotation=90, ha="right",
                 va="center", fontsize=ps.SIZE_LABEL, color=ps.INK)

    ps.panel_labels(fig, {letter: axes[r] for r, letter in enumerate(LETTERS)},
                    pad_pt=LETTER_PAD_PT)
    fig._fig07_rows = rows
    return fig


# --------------------------------------------------------------------------
# numbers for the caption and a geometry report
# --------------------------------------------------------------------------
def print_numbers(data: dict) -> None:
    for letter, (param, xlabel) in zip(LETTERS, ROWS):
        sub = data[param]
        print(f"({letter}) {param}: {xlabel}   reference = {sub.attrs['ref']:g}")
        print("     value   " + "".join(f"{c[0]:>22s}" for c in COLS)
              + "  overlay_links  trusted_sites  qkd_backed/qkd_preferred")
        for i, row in sub.iterrows():
            mark = "*" if i == sub.attrs["i_ref"] else " "
            print(f"   {mark} {_fmt(row['value']):>6s}  "
                  f"{int(row['physical_qkd_hops']):>22d}{row['qkd_backed_rekey_pct']:>22.1f}"
                  f"{row['min_pool_fraction']:>22.2f}  {int(row['qkd_overlay_links']):>13d}"
                  f"  {int(row['trusted_sites']):>13d}  "
                  f"{int(row['qkd_backed_rekeys'])}/{int(row['qkd_preferred_rekeys'])}")


def print_geometry(fig) -> None:
    ren = fig.canvas.get_renderer()
    W, H = fig.get_size_inches()
    dpi = fig.dpi
    ax0 = fig.axes[0]
    print(f"\nfigure {W:.2f} x {H:.2f} in; panel {ax0.get_position().width * W:.3f} x "
          f"{ax0.get_position().height * H:.3f} in")
    letters = sorted((t for t in fig.texts if t.get_gid() == "panel-label"),
                     key=lambda t: -t.get_position()[1])
    for r, row in enumerate(fig._fig07_rows):
        ax = fig.axes[3 * r]
        bbs = [t.get_window_extent(ren) for t in ax.get_xticklabels()]
        axbb = ax.get_window_extent(ren)
        over = max(axbb.x0 - bbs[0].x0, bbs[-1].x1 - axbb.x1) / dpi * 72
        if row["stagger"]:
            gaps = [(b2.x0 - b1.x1) / dpi * 72 for b1, b2 in zip(bbs[:-2], bbs[2:])]
            vgap = min(bbs[i].y0 - bbs[i + 1].y1 for i in range(0, len(bbs) - 1, 2)) / dpi * 72
            how = (f"two lines (single-line gap would be {row['gap_pt']:.1f} pt; "
                   f"lines {vgap:.1f} pt apart)")
        else:
            gaps = [(b2.x0 - b1.x1) / dpi * 72 for b1, b2 in zip(bbs[:-1], bbs[1:])]
            how = "one line"
        line = (f"{row['param']:22s} xlim {ax.get_xlim()[0]:+.3f}..{ax.get_xlim()[1]:.3f}  "
                f"{how}; min gap between neighbouring labels {min(gaps):.1f} pt; "
                f"end-label overhang {over:.1f} pt")
        if r > 0:
            xl = fig.axes[3 * (r - 1) + 1].xaxis.get_label().get_window_extent(ren)
            lb = letters[r].get_window_extent(ren)
            line += f"; x label of row above -> letter: {(xl.y0 - lb.y1) / dpi * 72:.1f} pt"
        print(line)


if __name__ == "__main__":
    from hybridsim.figcheck import lint
    ps.apply_style()
    print_numbers(table())
    fig = draw()
    print_geometry(fig)
    print("lint:", lint(fig) or "clean")
