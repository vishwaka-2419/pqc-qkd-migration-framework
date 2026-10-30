"""Figure 2 -- attenuation envelope, qualified QKD routes and long-haul route
qualification (manuscript QTC-2026-07-0055.R1, IET Quantum Communication).

(a) planning-envelope secret-key rate of one fibre span versus span length
    (logarithmic y axis) with the planning floor $R_{\\min}$, the designed hop
    limit and the per-hop operating points of every qualified route;
(b) route length of the six long-haul (core) routes, sorted by length, with
    the qualification outcome of the route planner.

Both panels are stacked at full text width: the per-route annotations of (b)
are about 1.9 in wide at the mandatory 8.5 pt, which no side-by-side layout
can hold without shrinking the bars to a sliver.

Run as a script to print the numbers quoted in the caption:

    python3 -m figures_src.fig02_envelope
"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Patch

from hybridsim import plotstyle as ps
from figures_src._data import DEFAULT, plan_qkd_link, reference, skr_point_to_point

# Link kinds that are candidates for a QKD service (access links are not).
KINDS = ("dci", "metro", "core")

# Planner reason -> short form printed next to the bars of panel (b).
REASON = {
    "qualified route": "qualified",
    "trusted-node policy limit exceeded": "trusted-node limit exceeded",
    "insufficient approved trusted sites": "approved sites insufficient",
    "no qualified optical path": "no qualified optical path",
    "per-hop SKR below planning floor": "per-hop rate below $R_{\\min}$",
}

# Link kind -> (marker, marker area in pt^2, colour, legend label) for the
# operating points of (a). The areas are kept small (about 4.5 pt across) so
# that the two DCI points, only 2.4 km apart, do not overlap; the triangle gets
# a larger area so that it reads as large as the circle and the square.
STYLE = {
    "dci": ("o", 20, ps.HUE[800], "DCI direct span"),
    "metro": ("s", 18, ps.HUE[500], "metro direct span"),
    "core": ("^", 30, ps.HUE[300], "core route, per hop"),
}

MARKER_HALO = 1.9         # white halo under each marker of (a): same shape, 1.9x the area

D_MAX_KM = 230.0          # extent of the envelope computation (NaN beyond ~200 km)
X_MAX_A_KM = 205.0        # x axis of (a): ends just past the drawn envelope (200 km)
B_AXIS_KM = 500.0         # x axis (spine and ticks) of (b): covers every bar
B_XLIM_KM = 790.0         # data limit of (b): room for the annotations right of the bars
Y_LIM = (30.0, 6.0e6)     # bit/s, log axis of (a)
HALO = dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none")
LEGEND_BG = dict(frameon=True, facecolor="white", edgecolor="none", framealpha=1.0)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def routes():
    """Return (qualified, core): lists of (link, plan) pairs.

    ``qualified`` holds every candidate link whose route the planner accepts
    (DCI and metro direct spans, core trusted-node routes); ``core`` holds the
    six long-haul routes sorted by length. Metro links without a dedicated
    optical path are skipped, as in the previous release.
    """
    qualified, core = [], []
    for link in reference().links:
        if link.kind not in KINDS:
            continue
        if link.kind == "metro" and not link.qkd_resources.dedicated_optical_path:
            continue
        plan = plan_qkd_link(link.distance_km, link.qkd_resources, DEFAULT.r_min_bps)
        if plan.feasible:
            qualified.append((link, plan))
        if link.kind == "core":
            core.append((link, plan))
    core.sort(key=lambda lp: lp[0].distance_km)
    return qualified, core


def envelope(step_km: float = 0.25):
    """Span length (km) and single-span envelope rate (bit/s, NaN below R_min)."""
    d = np.arange(1.0, D_MAX_KM + step_km / 2, step_km)
    r = np.array([skr_point_to_point(x, DEFAULT.r_min_bps) for x in d])
    return d, np.where(r > 0, r, np.nan)


def envelope_floor_km() -> float:
    """Longest span (km, 0.01 km resolution) whose envelope rate is >= R_min."""
    d = np.arange(1.0, D_MAX_KM, 0.01)
    ok = np.array([skr_point_to_point(x, DEFAULT.r_min_bps) > 0 for x in d])
    return float(d[ok].max())


def row_text(plan) -> str:
    """Annotation of one core route in panel (b)."""
    reason = REASON.get(plan.reason, plan.reason)
    hops = f"{plan.n_physical_hops} hops · " if plan.n_physical_hops else ""
    return hops + reason


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def _panel_a(ax, qualified):
    d, r = envelope()
    ax.plot(d, r, color=ps.HUE[900], lw=1.4, zorder=3, label="single-span envelope")
    ax.set_yscale("log")
    ax.set_xlim(0, X_MAX_A_KM)
    ax.set_ylim(*Y_LIM)
    ax.set_xticks(np.arange(0, X_MAX_A_KM, 50))

    # reference lines: planning floor (dotted) and designed hop limit (dashed)
    r_min, hop = DEFAULT.r_min_bps, DEFAULT.max_hop_km
    ax.axhline(r_min, ls=":", lw=1.0, color=ps.INK3, zorder=2)
    ax.axvline(hop, ls="--", lw=0.9, color=ps.INK3, zorder=2)
    # Both labels sit between grid lines: the floor label just above the dotted
    # line at the far left, the hop-limit label left of the dashed line near the
    # top, where the envelope has not yet arrived.
    ax.text(4, r_min * 1.3, f"planning floor $R_{{\\min}}$ = {r_min:g} bit/s",
            ha="left", va="bottom", fontsize=ps.SIZE_ANNOT, color=ps.INK2, zorder=5)
    ax.text(hop - 3, 2.5e6, f"designed hop limit ({hop:g} km)",
            ha="right", va="center", fontsize=ps.SIZE_ANNOT, color=ps.INK2, zorder=5)

    # Operating points of the qualified routes at (per-hop length, per-hop
    # rate). The DCI and metro points at 37.5, 39.9 and 42.6 km are close: the
    # small marker areas of STYLE keep them apart, and a white halo under each
    # marker (all halos drawn before all markers) lifts them off the envelope
    # line, so that no sliver of the line shows between neighbouring markers.
    points = {kind: sorted((p.hop_km, p.skr_bps) for l, p in qualified if l.kind == kind)
              for kind in STYLE}
    for kind, (marker, area, colour, label) in STYLE.items():
        if points[kind]:
            ax.scatter([x for x, _ in points[kind]], [y for _, y in points[kind]],
                       marker=marker, s=MARKER_HALO * area, color="white",
                       edgecolor="none", zorder=3.5)
    for kind, (marker, area, colour, label) in STYLE.items():
        if points[kind]:
            ax.scatter([x for x, _ in points[kind]], [y for _, y in points[kind]],
                       marker=marker, s=area, color=colour, edgecolor="white",
                       linewidth=0.8, zorder=4, label=label)

    # direct labels of the trusted-node routes, in the free space right of the
    # points (and of the hop limit), each between two grid lines
    core = [(l, p) for l, p in qualified if l.kind == "core"]
    core.sort(key=lambda lp: -lp[1].skr_bps)            # highest rate first
    label_x = 95.0                                      # km
    label_y = [2.0e5, 4.0e4]                            # bit/s
    for (link, plan), y in zip(core, label_y):
        ax.plot([plan.hop_km, label_x - 1.5], [plan.skr_bps, y], color=ps.INK3,
                lw=0.6, zorder=3.8)          # leader line: above the halo, below the marker
        ax.text(label_x, y, f"{link.link_id}: {plan.n_physical_hops} × {plan.hop_km:.0f} km",
                ha="left", va="center", fontsize=ps.SIZE_ANNOT, color=ps.INK2, zorder=5)

    ax.set_xlabel("span length (km)")
    ax.set_ylabel("planning-envelope\nsecret-key rate (bit/s)")
    ax.legend(loc="upper right", **LEGEND_BG)


def _panel_b(ax, core):
    y = np.arange(len(core))
    for yi, (link, plan) in zip(y, core):
        if plan.feasible:
            ax.barh(yi, link.distance_km, height=0.6, color=ps.HUE[800], edgecolor="none")
        else:
            ax.barh(yi, link.distance_km, height=0.6, color=ps.NEUTRAL, hatch="////",
                    edgecolor=ps.INK3, linewidth=0)
        # white halo: the vertical grid lines stop at the text instead of
        # running through it
        ax.text(link.distance_km + 10, yi, row_text(plan), ha="left", va="center",
                fontsize=ps.SIZE_ANNOT, color=ps.INK2, zorder=5, bbox=HALO)
    ax.set_yticks(y)
    ax.set_yticklabels([l.link_id for l, _ in core])
    ax.set_ylim(len(core) - 0.4, -0.6)                 # shortest route on top
    ax.set_xlim(0, B_XLIM_KM)                            # room for the annotations
    ax.set_xticks(np.arange(0, B_AXIS_KM + 1, 100))      # axis covers every bar
    ax.spines["bottom"].set_bounds(0, B_AXIS_KM)         # ... and stops there
    ax.grid(axis="x")
    ax.grid(False, axis="y")
    ax.set_xlabel("route length (km)")
    # Centre the x label on the drawn axis (0-500 km) instead of on the wider
    # axes box: the label's x is an axes fraction; its y stays automatic.
    ax.xaxis.label.set_x(0.5 * B_AXIS_KM / B_XLIM_KM)
    ax.set_ylabel("core route")
    handles = [Patch(facecolor=ps.HUE[800], edgecolor="none", label="qualified route"),
               Patch(facecolor=ps.NEUTRAL, edgecolor=ps.INK3, hatch="////", linewidth=0,
                     label="rejected route")]
    ax.legend(handles=handles, loc="upper right", **LEGEND_BG)


def _align_ylabels(fig, ax_a, ax_b):
    """Shift the y label of (b) so that both y labels start at the same x.

    ``panel_labels`` puts each letter at the left edge of the panel's tight
    bounding box, which here is the y label; equal left edges give aligned
    letters.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    x_a = ax_a.yaxis.label.get_window_extent(renderer).x0
    x_b = ax_b.yaxis.label.get_window_extent(renderer).x0
    delta_pt = (x_b - x_a) * 72 / fig.dpi
    if delta_pt > 0:
        ax_b.yaxis.labelpad += delta_pt
    else:
        ax_a.yaxis.labelpad -= delta_pt


def draw():
    qualified, core = routes()
    fig = ps.figure(1.0, 4.8)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.95, 1.5], left=0.118, right=0.995,
                          top=0.958, bottom=0.09, hspace=0.42)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    _panel_a(ax_a, qualified)
    _panel_b(ax_b, core)
    _align_ylabels(fig, ax_a, ax_b)
    ps.panel_labels(fig, {"a": ax_a, "b": ax_b})
    return fig


# --------------------------------------------------------------------------
# numbers for the caption
# --------------------------------------------------------------------------
def main():
    from hybridsim.qkd import ALPHA_DB_PER_KM, R0_BPS, SYSTEM_LOSS_DB

    qualified, core = routes()
    print(f"envelope model: {R0_BPS / 1e6:g} Mbit/s at zero loss, {ALPHA_DB_PER_KM:.2f} dB/km "
          f"fibre attenuation plus {SYSTEM_LOSS_DB:g} dB system loss")
    print(f"planning floor R_min = {DEFAULT.r_min_bps:g} bit/s; designed hop limit = "
          f"{DEFAULT.max_hop_km:g} km; trusted-node policy limit = {DEFAULT.trusted_node_limit}; "
          f"envelope reaches R_min at {envelope_floor_km():.1f} km")
    print(f"envelope at 1 km: {skr_point_to_point(1.0):.0f} bit/s; at {DEFAULT.max_hop_km:g} km: "
          f"{skr_point_to_point(DEFAULT.max_hop_km):.0f} bit/s")
    print("qualified routes (per-hop length, per-hop envelope rate; caption rounding in brackets):")
    for link, plan in sorted(qualified, key=lambda lp: lp[1].hop_km):
        print(f"  {link.link_id:9s} {link.kind:5s} {link.distance_km:6.1f} km  "
              f"{plan.n_physical_hops} hop(s) x {plan.hop_km:5.1f} km  "
              f"{plan.n_trusted_nodes} trusted node(s)  {plan.skr_bps / 1e3:6.1f} kbit/s  "
              f"[{plan.hop_km:.1f} km, {plan.skr_bps / 1e3:.0f} kbit/s]")
    print("core routes sorted by length:")
    for link, plan in core:
        res = link.qkd_resources
        print(f"  {link.link_id:7s} {link.distance_km:6.1f} km [{link.distance_km:.0f}]  "
              f"{plan.n_physical_hops} hops  {plan.n_trusted_nodes} trusted nodes needed, "
              f"{res.trusted_sites_available} approved, policy limit "
              f"{res.max_trusted_nodes_policy}, optical path {res.dedicated_optical_path}"
              f"  -> {row_text(plan)}")
    n_q = len(qualified)
    hops = sum(p.n_physical_hops for _, p in qualified)
    sites = sum(p.n_trusted_nodes for _, p in qualified)
    print(f"{n_q} qualified routes, {hops} physical hops, {sites} trusted sites in total")


if __name__ == "__main__":
    main()
