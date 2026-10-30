"""Figure 9 -- the proposed policy versus five alternative planning and gating schemes.

Five horizontal-bar panels (a)-(e) with a shared categorical y axis that lists
the six schemes A-F of Table tab:baselines (``results/sensitivity/baselines.csv``,
one 24-h run each on the reference scenario). The proposed scheme F is drawn
in ``ps.EMPHASIS``, the comparison schemes A-E in ``ps.MUTED``; every value is
printed at the end of its bar, and a metric that is undefined for a scheme
(scheme A has no QKD-preferred rekeys and no KME pool) gets no bar and "n/a".
Nothing but numbers and axis labels is written inside the figure -- the
explanation lives in ``captions/Figure_9.tex``.

Run ``python3 -m figures_src.fig09_baselines`` to print the plotted numbers.
"""
from __future__ import annotations

import math

import numpy as np

from hybridsim import plotstyle as ps
from figures_src._data import sensitivity

# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------
# (row key in baselines.csv, two-line y tick label).  The continuation line is
# indented so that the scheme letters A-F form a column at the left.
SCHEMES = [
    ("A_pqc_only_no_qkd",                 "A  PQC/PQ-T only,\n    no QKD"),
    ("B_qkd_all_feasible_links",          "B  QKD on every\n    feasible link"),
    ("C_selective_static_threshold",      "C  selective,\n    static 20 % pool gate"),
    ("D_selective_reactive_only",         "D  selective,\n    reactive fallback only"),
    ("E_selective_no_hysteresis",         "E  selective,\n    no re-entry hysteresis"),
    ("F_proposed_selective_reserve_time", "F  proposed (selective,\n    reserve-time, hysteresis)"),
]
PROPOSED = "F_proposed_selective_reserve_time"
# metrics that are undefined for a scheme (no bar, "n/a" next to the axis):
# scheme A plans no QKD, so it has no QKD-preferred rekeys and no KME pool
NOT_APPLICABLE = {("A_pqc_only_no_qkd", "qkd_backed_rekey_pct"),
                  ("A_pqc_only_no_qkd", "min_pool_fraction")}

# (metric column, x label, value format, scale, bracketed column, tick cap)
PANELS = [
    ("qkd_backed_rekey_pct", "QKD-backed\nrekeys (%)",           "{:.1f}", 1.0,   None,                       100.0),
    ("physical_qkd_hops",    "physical\nQKD hops",               "{:d}",   1.0,   "trusted_sites",            None),
    ("min_pool_fraction",    "minimum\npool level\n(fraction)",  "{:.2f}", 1.0,   None,                       1.0),
    ("kme_errors",           "hard KME\nstarvation\nevents",     "{:d}",   1.0,   "reactive_fallback_rekeys", None),
    ("premium_npv_kEUR",     "five-year\nassurance\npremium (MEUR)", "{:.2f}", 1e-3, None,                   None),
]

# --------------------------------------------------------------------------
# geometry (inches); the label column and the x limits are measured, not guessed
# --------------------------------------------------------------------------
HEIGHT = 3.6
PANEL_W = [0.80, 0.74, 0.70, 1.00, 0.91]   # data areas of (a)-(e); (d) carries the longest label
GAP = 0.12                                 # between neighbouring panels
MARGIN_L, MARGIN_R = 0.03, 0.08            # right margin takes the overhang of the (e) x label
LABEL_GAP = 0.08                           # between the scheme labels and the axis of (a)
TOP_SPACE = 0.22                           # room for the panel letters
BOTTOM_SPACE = 0.80                        # tick labels + three-line x labels
BAR_H = 0.62
VALUE_GAP_PT = 3.0                         # bar end -> value label
VALUE_MARGIN = 0.03                        # value label -> right edge of the panel


def table():
    """The baseline rows in display order A-F (one row per scheme)."""
    df = sensitivity("baselines").set_index("parameter")
    return df.loc[[key for key, _ in SCHEMES]]


def _fmt(value: float, fmt: str) -> str:
    if value == 0:
        return "0"
    return fmt.format(int(round(value)) if fmt == "{:d}" else value)


def _thousands(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def value_labels(df) -> list[list[str]]:
    """The text printed at the end of every bar, per panel, rows A-F."""
    out = []
    for col, _, fmt, scale, bracket, _ in PANELS:
        labels = []
        for key, _ in SCHEMES:
            if (key, col) in NOT_APPLICABLE:
                labels.append("n/a")
                continue
            txt = _fmt(df.at[key, col] * scale, fmt)
            if bracket is not None:
                b = df.at[key, bracket]
                txt += f" ({_thousands(b) if b >= 1000 else int(round(b))})"
            labels.append(txt)
        out.append(labels)
    return out


def _ticks(xmax: float, cap: float | None) -> list[float]:
    """0 and the largest 'nice' step that gives at least two further ticks
    inside 92 % of the axis (and never beyond ``cap``, e.g. 100 %)."""
    reach = 0.92 * xmax if cap is None else min(0.92 * xmax, cap)
    best = None
    for k in range(-3, 6):
        for m in (1, 2, 2.5, 4, 5):
            step = m * 10.0 ** k
            n = math.floor(reach / step + 1e-9)
            if n >= 2 and (best is None or step > best):
                best = step
    n = math.floor(reach / best + 1e-9)
    return [i * best for i in range(n + 1)]


def draw():
    df = table()
    labels = value_labels(df)
    n = len(SCHEMES)
    y = np.arange(n)
    colours = [ps.EMPHASIS if key == PROPOSED else ps.MUTED for key, _ in SCHEMES]

    fig = ps.figure(1.0, HEIGHT)
    fig_w, fig_h = fig.get_size_inches()
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()

    # width of the scheme-label column, measured in the final font
    probes = [fig.text(0, 0, lab, fontsize=ps.SIZE_TICK) for _, lab in SCHEMES]
    col_w = max(t.get_window_extent(ren).width for t in probes) / fig.dpi
    for t in probes:
        t.remove()

    left = (MARGIN_L + col_w + LABEL_GAP) / fig_w
    gs = fig.add_gridspec(1, len(PANELS), width_ratios=PANEL_W,
                          wspace=GAP / np.mean(PANEL_W),
                          left=left, right=1 - MARGIN_R / fig_w,
                          top=1 - TOP_SPACE / fig_h, bottom=BOTTOM_SPACE / fig_h)
    axes = []
    for i, (col, xlabel, fmt, scale, bracket, cap) in enumerate(PANELS):
        ax = fig.add_subplot(gs[0, i], sharey=axes[0] if axes else None)
        axes.append(ax)
        na = np.array([(key, col) in NOT_APPLICABLE for key, _ in SCHEMES])
        vals = np.where(na, 0.0, df[col].to_numpy(dtype=float) * scale)
        ax.grid(False)                 # every value is printed; no grid to cut
        ax.barh(y, vals, height=BAR_H, color=colours, edgecolor="none", zorder=2)
        texts = []
        for yi, v, txt, undefined in zip(y, vals, labels[i], na):
            texts.append(ax.annotate(
                txt, (v, yi), xytext=(VALUE_GAP_PT, 0), textcoords="offset points",
                ha="left", va="center", fontsize=ps.SIZE_ANNOT,
                color=ps.INK3 if undefined else ps.INK2, zorder=3))
        ax.set_xlabel(xlabel, labelpad=4)
        ax.tick_params(axis="y", length=0, labelleft=(i == 0))
        ax._lint_values = (vals, texts, cap)

    ax0 = axes[0]
    ax0.set_yticks(y)
    ax0.set_yticklabels([lab for _, lab in SCHEMES], ha="left")
    ax0.tick_params(axis="y", pad=(col_w + LABEL_GAP) * 72)
    ax0.set_ylim(n - 1 + 0.65, -0.65)          # A at the top, F at the bottom

    # x limits: the longest value label must end inside its panel
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    gap_px = VALUE_GAP_PT / 72 * fig.dpi
    margin_px = VALUE_MARGIN * fig.dpi
    for ax in axes:
        vals, texts, cap = ax._lint_values
        width_px = ax.get_window_extent(ren).width
        xmax = 0.0
        for v, t in zip(vals, texts):
            free = width_px - gap_px - t.get_window_extent(ren).width - margin_px
            xmax = max(xmax, v * width_px / free)
        ax.set_xlim(0, xmax)
        ticks = _ticks(xmax, cap)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t:g}" for t in ticks])
        ax.spines["bottom"].set_bounds(0, ticks[-1])   # the axis line ends at the last tick
        del ax._lint_values

    # the letter of (a) belongs above its axis line, not above the scheme-label
    # column: hide the tick labels while the letters are placed
    ax0.tick_params(axis="y", labelleft=False)
    ps.panel_labels(fig, dict(zip("abcde", axes)))
    ax0.tick_params(axis="y", labelleft=True)
    return fig


if __name__ == "__main__":
    from hybridsim.figcheck import lint
    ps.apply_style()
    df = table()
    labels = value_labels(df)
    print("scheme  " + "  ".join(f"{col:>24s}" for col, *_ in PANELS))
    for r, (key, _) in enumerate(SCHEMES):
        print(f"{key[0]:6s}  " + "  ".join(f"{labels[i][r]:>24s}" for i in range(len(PANELS))))
    print("\nraw rows (qkd_overlay_links, physical_qkd_hops, trusted_sites, qkd_preferred_rekeys, "
          "qkd_backed_rekeys, qkd_backed_rekey_pct, min_pool_fraction, kme_errors, "
          "reactive_fallback_rekeys, proactive_demotion_transition_sessions, mode_transitions, "
          "hybrid_npv_kEUR, premium_npv_kEUR):")
    cols = ["qkd_overlay_links", "physical_qkd_hops", "trusted_sites", "qkd_preferred_rekeys",
            "qkd_backed_rekeys", "qkd_backed_rekey_pct", "min_pool_fraction", "kme_errors",
            "reactive_fallback_rekeys", "proactive_demotion_transition_sessions",
            "mode_transitions", "hybrid_npv_kEUR", "premium_npv_kEUR"]
    for key, _ in SCHEMES:
        print(f"{key[0]}: " + ", ".join(str(df.at[key, c]) for c in cols))
    fig = draw()
    for letter, ax in zip("abcde", fig.axes):
        print(f"({letter}) xlim 0-{ax.get_xlim()[1]:.4g}, ticks {ax.get_xticks().tolist()}")
    print("lint:", lint(fig) or "clean")
