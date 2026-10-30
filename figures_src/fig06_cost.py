"""Figure 6 -- illustrative cost model with physical-hop accounting.

(a) itemised five-year NPV of the twelve cost items, split into the items
    shared by both strategies and the items incremental to the selective QKD
    overlay (horizontal bars, hatch = opex);
(b) five-year NPV cost of both strategies versus the QKD endpoint-pair capex
    per physical hop, the gap being the assurance premium;
(c) assurance premium versus discount rate for 5-, 7- and 10-year horizons.

All numbers come from ``hybridsim.tco.five_year_tco`` applied to the
reference scenario (``figures_src._data.reference()``).
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from hybridsim import plotstyle as ps
from figures_src._data import reference, five_year_tco

# --------------------------------------------------------------------------
# data definitions
# --------------------------------------------------------------------------
SHORT_NAMES = {
    "Inventory and common policy platform": "Policy platform",
    "PQC integration (all services)": "PQC integration",
    "Migration programme, phases 1-2": "Programme, phases 1–2",
    "Common platform operations": "Platform operations",
    "PQC operations (all services)": "PQC operations",
    "QKD endpoint pairs (per physical hop)": "QKD endpoint pairs ({hops} hops)",
    "Trusted-site construction": "Trusted-site construction",
    "QKD service integration (per logical link)": "QKD service integration",
    "Optical engineering (per logical link)": "Optical engineering",
    "Migration programme, phase 3": "Programme, phase 3",
    "QKD operations (per physical hop)": "QKD operations",
    "Trusted-site operations": "Trusted-site operations",
}
CAPEX_SWEEP = np.arange(20, 141, 10, dtype=float)      # kEUR per physical hop
RATES = np.array([0.0, 0.02, 0.04, 0.06, 0.08, 0.10])    # discount rates
HORIZONS = (5, 7, 10)                                    # years

# --------------------------------------------------------------------------
# geometry (inches); the figure is drawn at the printed width ps.FULL
# --------------------------------------------------------------------------
HEIGHT_IN = 5.10
LEFT_A_IN = 1.80        # (a) axes left edge: room for the item names
WIDTH_A_IN = 1.85       # (a) data area
COL_GAP_IN = 0.74       # (a) right edge -> (b)/(c) axes left (y label + ticks)
RIGHT_IN = 6.18         # (b)/(c) axes right edge (room for the "140" tick label)
TOP_MARGIN_IN = 0.22    # room for the panel letters
BOTTOM_IN = 0.46        # x tick labels + x label of (a) and (c)
PANEL_H_IN = 1.76       # height of (b) and (c): taller than their y labels

# white backing so that the light grid never runs through text or a legend
HALO = dict(boxstyle="square,pad=0.3", facecolor=ps.SURFACE, edgecolor="none")
HALO_SMALL = dict(boxstyle="square,pad=0.15", facecolor=ps.SURFACE, edgecolor="none")
LEGEND_FRAME = dict(frameon=True, fancybox=False, facecolor=ps.SURFACE,
                    edgecolor="none", framealpha=1.0)


def fmt(v: float) -> str:
    """0-decimal kEUR with a space as thousands separator (e.g. '1 250')."""
    return f"{v:,.0f}".replace(",", " ")


def fmt1(v: float) -> str:
    return f"{v:,.1f}".replace(",", " ")


def data() -> dict:
    ref = reference()
    t = five_year_tco(ref.links)
    hops = t["n_physical_qkd_hops"]
    items = []
    for scope, kind, name, npv in t["breakdown"]:
        items.append((scope, kind, SHORT_NAMES[name].format(hops=hops), float(npv)))
    shared = [it for it in items if it[0] == "shared"]
    incr = [it for it in items if it[0] == "incremental"]
    sweep = [five_year_tco(ref.links, qkd_pair_capex=c) for c in CAPEX_SWEEP]
    pqc = np.array([s["pqc_only_npv"][-1] for s in sweep])
    hyb = np.array([s["hybrid_npv"][-1] for s in sweep])
    prem = {h: np.array([five_year_tco(ref.links, horizon_years=h, discount_rate=r)["premium_npv"]
                         for r in RATES]) for h in HORIZONS}
    return {
        "shared": shared, "incremental": incr,
        "shared_total": sum(it[3] for it in shared),
        "incr_total": sum(it[3] for it in incr),
        "pqc_npv": float(t["pqc_only_npv"][-1]), "hybrid_npv": float(t["hybrid_npv"][-1]),
        "premium": float(t["premium_npv"]),
        "hops": hops, "sites": t["n_trusted_sites"], "links": t["n_qkd_links"],
        "services": t["n_services"],
        "capex": CAPEX_SWEEP, "pqc_sweep": pqc, "hybrid_sweep": hyb,
        "ref_capex": float(t["assumptions"].qkd_pair_capex_per_physical_hop),
        "rates": RATES, "premium_by_horizon": prem,
    }


def _layout(fig):
    """Gridspec with the inch budget above: (a) tall left, (b)/(c) stacked right."""
    W, H = fig.get_figwidth(), fig.get_figheight()
    width_b = RIGHT_IN - LEFT_A_IN - COL_GAP_IN - WIDTH_A_IN
    span_w = RIGHT_IN - LEFT_A_IN
    w_avg = (WIDTH_A_IN + width_b) / 2
    wspace = COL_GAP_IN / w_avg
    span_h = H - TOP_MARGIN_IN - BOTTOM_IN
    hspace = span_h / PANEL_H_IN - 2
    gs = fig.add_gridspec(2, 2, left=LEFT_A_IN / W, right=RIGHT_IN / W,
                          bottom=BOTTOM_IN / H, top=(H - TOP_MARGIN_IN) / H,
                          width_ratios=[WIDTH_A_IN, width_b], wspace=wspace,
                          height_ratios=[1, 1], hspace=hspace)
    assert abs(span_w - (WIDTH_A_IN + width_b + COL_GAP_IN)) < 1e-9
    ax_a = fig.add_subplot(gs[:, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 1])
    return ax_a, ax_b, ax_c


def _panel_a(ax, d):
    xmax = 1900.0
    bar_h = 0.66
    shared, incr = d["shared"], d["incremental"]
    # rows: shared group on top (y = 12 .. 8), one empty row, incremental (6 .. 0)
    rows = [(12 - i, it) for i, it in enumerate(shared)] + \
           [(6 - i, it) for i, it in enumerate(incr)]
    pad = 0.04 / WIDTH_A_IN * xmax          # 0.04 in between bar end and value
    for y, (scope, kind, name, v) in rows:
        face = ps.MUTED if scope == "shared" else ps.EMPHASIS
        hatch = ps.HATCHES[1] if kind == "opex" else ps.HATCHES[0]
        # the hatch is drawn in the edge colour (an invisible 0-pt edge); the
        # hatchcolor= property would need Matplotlib >= 3.11
        hatch_colour = ps.HUE[700] if scope == "shared" else ps.HUE[200]
        ax.barh(y, v, height=bar_h, color=face, hatch=hatch, edgecolor=hatch_colour,
                linewidth=0, zorder=3)
        ax.text(v + pad, y, fmt(v), ha="left", va="center",
                fontsize=ps.SIZE_ANNOT, color=ps.INK2, bbox=HALO_SMALL)
    ax.set_yticks([y for y, _ in rows])
    ax.set_yticklabels([it[2] for _, it in rows])
    ax.set_ylim(-0.7, 12.7)
    ax.set_xlim(0, xmax)
    ax.set_xticks([0, 500, 1000, 1500])
    ax.set_xlabel("five-year NPV (kEUR)")
    ax.grid(False)                     # every value is printed; no grid to cut
    ax.tick_params(axis="y", length=0)
    # group totals, right-aligned in the free space right of the short bars
    x_text = xmax - 0.03 / WIDTH_A_IN * xmax
    ax.text(x_text, 8.9, "shared by\nboth strategies\ntotal "
            f"{fmt1(d['shared_total'])} kEUR", ha="right", va="center",
            fontsize=ps.SIZE_ANNOT, color=ps.INK, linespacing=1.25, bbox=HALO)
    ax.text(x_text, 3.0, "incremental to the\nselective overlay\ntotal "
            f"{fmt1(d['incr_total'])} kEUR", ha="right", va="center",
            fontsize=ps.SIZE_ANNOT, color=ps.INK, linespacing=1.25, bbox=HALO)
    handles = [
        Patch(facecolor=ps.MUTED, edgecolor=ps.MUTED, linewidth=0, label="shared"),
        Patch(facecolor=ps.EMPHASIS, edgecolor=ps.EMPHASIS, linewidth=0, label="incremental"),
        Patch(facecolor=ps.SURFACE, edgecolor=ps.INK2, linewidth=0.7, label="capex"),
        Patch(facecolor=ps.SURFACE, edgecolor=ps.INK2, linewidth=0.7,
              hatch=ps.HATCHES[1], label="opex"),
    ]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.0),
              handlelength=1.6, handleheight=0.9, labelspacing=0.45, **LEGEND_FRAME)


def _panel_b(ax, d):
    capex, pqc, hyb = d["capex"], d["pqc_sweep"], d["hybrid_sweep"]
    ax.fill_between(capex, pqc, hyb, color=ps.HUE[100], alpha=0.5, lw=0, zorder=1)
    ax.plot(capex, hyb, color=ps.HUE[800], ls=ps.LINESTYLES[0], zorder=3,
            label="PQC + selective QKD")
    ax.plot(capex, pqc, color=ps.HUE[500], ls=ps.LINESTYLES[1], zorder=3,
            label="PQC migration baseline")
    # reference capex (model default): dotted segment spanning the premium
    ref = d["ref_capex"]
    pqc_ref = float(np.interp(ref, capex, pqc))
    hyb_ref = float(np.interp(ref, capex, hyb))
    ax.plot([ref, ref], [pqc_ref, hyb_ref], ls=":", color=ps.INK3, lw=0.9, zorder=2)
    ax.set_xlim(capex[0], capex[-1])
    ax.set_ylim(0, 5000)
    ax.set_xticks(np.arange(20, 141, 20))
    ax.set_yticks([0, 2000, 4000])
    ax.set_yticks([1000, 3000], minor=True)
    ax.set_xlabel("QKD endpoint-pair capex\nper physical hop (kEUR)")
    ax.set_ylabel("five-year NPV cost (kEUR)")
    # direct labels at the right ends of the lines (the panel is too narrow
    # for a legend); the fill label sits between the 2000 and 4000 grid lines
    ax.text(capex[-1] - 0.5, hyb[-1] + 160, "PQC + selective QKD", ha="right",
            va="bottom", fontsize=ps.SIZE_ANNOT, color=ps.INK)
    ax.text(capex[-1] - 0.5, 0.5 * pqc[-1], "PQC migration baseline", ha="right",
            va="center", fontsize=ps.SIZE_ANNOT, color=ps.INK)
    ax.text(60.0, 2500.0, "assurance premium", ha="center", va="center",
            fontsize=ps.SIZE_ANNOT, color=ps.INK2)


def _panel_c(ax, d):
    rates = d["rates"] * 100
    for h, c, ls, m in zip(HORIZONS, ps.SHADES, ps.LINESTYLES, ps.MARKERS):
        ax.plot(rates, d["premium_by_horizon"][h], color=c, ls=ls, marker=m,
                mec=ps.SURFACE, mew=0.6, label=f"{h}-year horizon", zorder=3)
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(0, 4400)
    ax.set_xticks(np.arange(0, 11, 2))
    ax.set_yticks([0, 2000, 4000])
    ax.set_yticks([1000, 3000], minor=True)
    ax.set_xlabel("discount rate (%)")
    ax.set_ylabel("assurance premium (kEUR)")
    ax.legend(loc="lower left", **LEGEND_FRAME)


def draw():
    d = data()
    fig = ps.figure(1.0, HEIGHT_IN)
    ax_a, ax_b, ax_c = _layout(fig)
    _panel_a(ax_a, d)
    _panel_b(ax_b, d)
    _panel_c(ax_c, d)
    ps.panel_labels(fig, {"a": ax_a, "b": ax_b, "c": ax_c}, pad_pt=4.0)
    return fig


if __name__ == "__main__":
    ps.apply_style()
    d = data()
    print(f"reference overlay: {d['links']} logical links, {d['hops']} physical hops, "
          f"{d['sites']} trusted sites, {d['services']} services")
    print("(a) itemised five-year NPV (kEUR):")
    for scope in ("shared", "incremental"):
        for s, kind, name, v in d[scope]:
            print(f"    {s:12s} {kind:5s} {name:32s} {v:8.1f}  -> label {fmt(v)}")
    print(f"    shared total      {d['shared_total']:.1f}  (= PQC baseline NPV {d['pqc_npv']:.1f})")
    print(f"    incremental total {d['incr_total']:.1f}  (= premium {d['premium']:.1f}; "
          f"hybrid NPV {d['hybrid_npv']:.1f})")
    print("(b) capex sweep (kEUR per hop -> PQC baseline, PQC + selective QKD, premium):")
    for c, p, h in zip(d["capex"], d["pqc_sweep"], d["hybrid_sweep"]):
        print(f"    {c:5.0f}  {p:8.1f}  {h:8.1f}  {h - p:8.1f}")
    slope = (d["hybrid_sweep"][-1] - d["hybrid_sweep"][0]) / (d["capex"][-1] - d["capex"][0])
    print(f"    slope {slope:.2f} kEUR of NPV per kEUR of pair capex")
    print("(c) assurance premium (kEUR) vs discount rate:")
    print("    rate (%): " + "  ".join(f"{r * 100:6.0f}" for r in d["rates"]))
    for h in HORIZONS:
        vals = d["premium_by_horizon"][h]
        print(f"    {h:2d}-year: " + "  ".join(f"{v:6.1f}" for v in vals)
              + f"   (range {vals.min():.1f}-{vals.max():.1f})")
    fig = draw()
    from hybridsim.figcheck import lint
    issues = lint(fig)
    print("lint:", issues if issues else "clean")
