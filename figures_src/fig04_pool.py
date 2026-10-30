"""Figure 4 -- paired-KME pool dynamics and the reserve-time signal under
link-specific QKD refill outages (24-h reference simulation).

Two stacked panels with a shared time axis:

(a) pool level (Mbit) of the three traced overlay links, the two refill-outage
    windows as shaded spans with a label above the data, and the protected
    reserve ``beta * B_max`` as a dotted reference line;
(b) the predicted reserve time (h) that the gating rule compares with the SLA
    margin, with the gold demotion margin ``T_min`` (dashed) and the re-entry
    threshold ``kappa * T_min`` (dotted) labelled outside the axes on the
    right, where nothing else is.

Series identity is carried by shade *and* line style (solid / dashed /
dotted) so the figure also reads in greyscale; one legend only, in the margin
column to the right of panel (a). Everything else is said in the caption.

Data: ``reference().result.link_runs`` (``pool_trace`` = (t_s, level_bits,
reserve_h) every 300 s for ``reference().trace_ids``), ``reference().outages``
and the planning parameters ``DEFAULT`` / ``MIN_RESERVE_S``.

``draw()`` returns the Figure. Run the module as a script
(``python3 -m figures_src.fig04_pool``) to print the numbers quoted in the
caption (full-pool reserve per link, crossing, demotion and re-entry times,
minimum levels, rekeys carried outside QKD during the demotion).
"""
from __future__ import annotations

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory

from hybridsim import plotstyle as ps
from hybridsim.modes import QKD_MODES
from figures_src._data import reference, DEFAULT, MIN_RESERVE_S, link_qkd_demand_bps

# ---------------------------------------------------------------- geometry (in)
WIDTH = 1.0            # fraction of the text width
HEIGHT_IN = 5.0        # total figure height
LEFT_IN = 0.64         # y labels + y tick labels
RIGHT_IN = 1.10        # margin column: legend of (a), reference-line labels of (b)
TOP_IN = 0.26          # room for the panel letter (a)
GAP_IN = 0.44          # between the panels: room for the panel letter (b)
BOTTOM_IN = 0.50       # x tick labels + x label
HEIGHT_RATIOS = (1.0, 1.05)
XPAD_IN = 0.07         # gap between the right spine and the margin column

# ------------------------------------------------------------------ panel (a)
YMAX_A = 6.3           # Mbit; leaves room for the outage labels above B_max
SPAN_TOP_A = 5.45      # Mbit; the shaded outage windows stop here in (a) ...
OUTAGE_LABEL_Y = 5.62  # Mbit; ... and are labelled just above
RESERVE_LABEL_DY = 0.10  # Mbit above the dotted protected-reserve line
RESERVE_LABEL_X = 23.6   # h, right-aligned

# ------------------------------------------------------------------ panel (b)
YMAX_B = 14.5          # h; shows the full range (core-0 sits at ~13 h)
REF_LABEL_DY = 0.12    # h between a reference line and its label

LINE_W = 1.4           # data lines
REF_W = 0.9            # reference lines
T_END_H = 24.0
X_LEAD_H = 0.3                  # hours of margin left of 00:00 (the initial fill stays visible)


# ---------------------------------------------------------------------- data
def load() -> dict:
    """Traces of the three traced links in plotting units plus the parameters."""
    ref = reference()
    runs = {lr.link.link_id: lr for lr in ref.result.link_runs
            if lr.link.link_id in ref.trace_ids and lr.pool_trace}
    series = {}
    for lid in ref.trace_ids:
        lr = runs[lid]
        trace = np.asarray(lr.pool_trace, dtype=float)
        series[lid] = {
            "t_h": trace[:, 0] / 3600.0,
            "level_mbit": trace[:, 1] / 1e6,
            "reserve_h": trace[:, 2],
            "capacity_mbit": lr.pool.capacity_bits / 1e6,
            "skr_bps": lr.pool.skr_bps,
            "demand_bps": link_qkd_demand_bps(lr.link),
            "distance_km": lr.link.distance_km,
            "run": lr,
        }
    capacities = {s["capacity_mbit"] for s in series.values()}
    assert len(capacities) == 1, "all traced pools share one capacity"
    capacity_mbit = capacities.pop()
    gold_h = MIN_RESERVE_S["gold"] / 3600.0 * DEFAULT.reserve_margin_scale
    return {
        "ref": ref,
        "series": series,
        "outages_h": {lid: (a / 3600.0, b / 3600.0) for lid, (a, b) in ref.outages.items()},
        "capacity_mbit": capacity_mbit,
        "protected_mbit": DEFAULT.protected_fraction * capacity_mbit,   # beta * B_max
        "gold_h": gold_h,                                                # T_min (gold)
        "reentry_h": gold_h * DEFAULT.reentry_multiplier,                # kappa * T_min
    }


def _styles(trace_ids) -> dict:
    """dci-0 solid HUE[800]; core-0 dashed HUE[500]; dci-1 dotted HUE[300]."""
    return {lid: {"color": ps.SHADES[i], "linestyle": ps.LINESTYLES[i]}
            for i, lid in enumerate(trace_ids)}


# ---------------------------------------------------------------------- draw
def draw():
    d = load()
    series, outages = d["series"], d["outages_h"]
    styles = _styles(d["ref"].trace_ids)

    fig = ps.figure(WIDTH, HEIGHT_IN)
    fig_w, fig_h = fig.get_size_inches()
    panel_h = (fig_h - TOP_IN - BOTTOM_IN - GAP_IN) / 2.0
    gs = fig.add_gridspec(2, 1, height_ratios=HEIGHT_RATIOS,
                          left=LEFT_IN / fig_w, right=1.0 - RIGHT_IN / fig_w,
                          top=1.0 - TOP_IN / fig_h, bottom=BOTTOM_IN / fig_h,
                          hspace=GAP_IN / panel_h)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1], sharex=ax_a)
    axes_w_in = fig_w - LEFT_IN - RIGHT_IN
    x_margin = 1.0 + XPAD_IN / axes_w_in          # axes fraction of the column start

    # shaded refill-outage windows: up to SPAN_TOP_A in (a) so that the label
    # sits above them, full height in (b)
    for lid, (a, b) in outages.items():
        ax_a.axvspan(a, b, ymax=SPAN_TOP_A / YMAX_A, facecolor=ps.HUE[100],
                     alpha=0.5, lw=0)
        ax_a.text(0.5 * (a + b), OUTAGE_LABEL_Y, f"{lid} refill outage",
                  ha="center", va="bottom", fontsize=ps.SIZE_ANNOT, color=ps.INK2)
        ax_b.axvspan(a, b, facecolor=ps.HUE[100], alpha=0.5, lw=0)

    # the three traces; the dotted light series is drawn last so that all
    # three remain visible where they coincide at B_max
    for lid in d["ref"].trace_ids:
        s = series[lid]
        ax_a.plot(s["t_h"], s["level_mbit"], lw=LINE_W, label=lid, **styles[lid])
        ax_b.plot(s["t_h"], s["reserve_h"], lw=LINE_W, label=lid, **styles[lid])

    # (a) protected reserve beta * B_max
    ax_a.axhline(d["protected_mbit"], ls=":", lw=REF_W, color=ps.INK3)
    ax_a.text(RESERVE_LABEL_X, d["protected_mbit"] + RESERVE_LABEL_DY,
              r"protected reserve $\beta B_{\max}$", ha="right", va="bottom",
              fontsize=ps.SIZE_ANNOT, color=ps.INK2)
    ax_a.set_ylim(0, YMAX_A)
    ax_a.set_yticks(np.arange(0, int(d["capacity_mbit"]) + 1, 1))
    ax_a.set_ylabel("paired-KME pool level (Mbit)")
    ax_a.tick_params(axis="x", labelbottom=False)

    # (b) gold demotion margin T_min and re-entry threshold kappa * T_min,
    # labelled in the margin column right of the axes
    ax_b.axhline(d["gold_h"], ls="--", lw=REF_W, color=ps.INK3)
    ax_b.axhline(d["reentry_h"], ls=":", lw=REF_W, color=ps.INK3)
    trans_b = blended_transform_factory(ax_b.transAxes, ax_b.transData)
    ax_b.text(x_margin, d["reentry_h"] + REF_LABEL_DY,
              "re-entry threshold\n" + rf"$\kappa T_{{\min}}$ = {d['reentry_h']:g} h",
              transform=trans_b, ha="left", va="bottom", clip_on=False,
              fontsize=ps.SIZE_ANNOT, color=ps.INK2, linespacing=1.15)
    ax_b.text(x_margin, d["gold_h"] - REF_LABEL_DY,
              rf"$T_{{\min}}$ = {d['gold_h']:g} h" + "\ndemotion margin",
              transform=trans_b, ha="left", va="top", clip_on=False,
              fontsize=ps.SIZE_ANNOT, color=ps.INK2, linespacing=1.15)
    # short leaders carry both reference lines into the margin column, so that
    # each label is tied to its line and not to the traces that end at the spine
    for yv, ls in ((d["gold_h"], "--"), (d["reentry_h"], ":")):
        ax_b.plot([1.0, x_margin - 0.003], [yv, yv], transform=trans_b, ls=ls,
                  lw=REF_W, color=ps.INK3, clip_on=False, zorder=2)
    ax_b.set_ylim(0, YMAX_B)
    ax_b.set_yticks(np.arange(0, YMAX_B, 2))
    ax_b.set_ylabel("predicted reserve time (h)")
    ax_b.set_xlim(-X_LEAD_H, T_END_H)        # the 00:00 start clear of the spine
    ax_b.set_xticks(np.arange(0, T_END_H + 0.5, 3))
    ax_b.set_xlabel("time of day (h)")

    # one legend, top of the margin column next to (a)
    handles = [Line2D([], [], lw=LINE_W, label=lid, **styles[lid])
               for lid in d["ref"].trace_ids]
    ax_a.legend(handles=handles, loc="upper left", bbox_to_anchor=(x_margin, 1.0),
                borderaxespad=0.0, borderpad=0.0, handlelength=2.6)

    fig.align_ylabels([ax_a, ax_b])           # common x for the y labels and letters
    ps.panel_labels(fig, {"a": ax_a, "b": ax_b})
    return fig


# ----------------------------------------------------------- caption numbers
def _hhmm(t_h: float) -> str:
    m = int(round(t_h * 60))
    return f"{m // 60:02d}:{m % 60:02d}"


def caption_numbers() -> dict:
    """Numbers quoted in the caption, all taken from the plotted data."""
    d = load()
    out = {"capacity_mbit": d["capacity_mbit"], "protected_mbit": d["protected_mbit"],
           "gold_h": d["gold_h"], "reentry_h": d["reentry_h"],
           "beta": DEFAULT.protected_fraction, "kappa": DEFAULT.reentry_multiplier,
           "links": {}}
    for lid, s in d["series"].items():
        t, lvl, res = s["t_h"], s["level_mbit"], s["reserve_h"]
        full = np.flatnonzero(lvl >= d["capacity_mbit"] - 1e-9)
        info = {
            "distance_km": s["distance_km"],
            "skr_bps": s["skr_bps"],
            "demand_bps": s["demand_bps"],
            "start_mbit": lvl[0],
            "first_full_h": t[full[0]] if len(full) else None,
            "full_reserve_h": (d["capacity_mbit"] - d["protected_mbit"]) * 1e6 / s["demand_bps"] / 3600,
            "min_mbit": lvl.min(), "t_min_mbit_h": t[lvl.argmin()],
            "min_reserve_h": res.min(), "t_min_reserve_h": t[res.argmin()],
            "outage_h": d["outages_h"].get(lid),
        }
        if lid in d["outages_h"]:
            a, b = d["outages_h"][lid]
            info["level_at_outage_end_mbit"] = lvl[np.searchsorted(t, b)]
            info["reserve_at_outage_end_h"] = res[np.searchsorted(t, b)]
            for name, thr in (("below_reentry_h", d["reentry_h"]), ("below_gold_h", d["gold_h"])):
                idx = np.flatnonzero((res < thr) & (t > a))
                info[name] = t[idx[0]] if len(idx) else None
        # demotion / re-entry events and rekeys carried outside QKD
        demotions, reentries, non_qkd, total, sessions = [], [], 0, 0, 0
        for sid, sr in s["run"].services.items():
            prev = None
            for t_s, mode, _ in sr.decision_log:
                if prev in QKD_MODES and mode not in QKD_MODES:
                    demotions.append((t_s / 3600, sid, mode))
                if prev is not None and prev not in QKD_MODES and mode in QKD_MODES:
                    reentries.append((t_s / 3600, sid, mode))
                prev = mode
            non_qkd += sum(v for m, v in sr.rekeys_by_mode.items() if m not in QKD_MODES)
            total += sr.rekeys
            sessions += sr.proactive_demotions
        info.update({"demotions": sorted(demotions), "reentries": sorted(reentries),
                     "demoted_sessions": sessions, "non_qkd_rekeys": non_qkd,
                     "rekeys": total, "services": len(s["run"].services),
                     "sla_classes": sorted({sr.service.sla_class
                                            for sr in s["run"].services.values()})})
        out["links"][lid] = info
    return out


if __name__ == "__main__":
    n = caption_numbers()
    print(f"pool capacity B_max = {n['capacity_mbit']:.2f} Mbit; protected reserve "
          f"beta*B_max = {n['protected_mbit']:.3f} Mbit (beta = {n['beta']})")
    print(f"gold demotion margin T_min = {n['gold_h']:g} h; re-entry threshold "
          f"kappa*T_min = {n['reentry_h']:g} h (kappa = {n['kappa']})")
    for lid, i in n["links"].items():
        print(f"\n{lid}: {i['distance_km']:.1f} km, SKR {i['skr_bps']:.0f} bit/s, "
              f"key demand {i['demand_bps']:.1f} bit/s, {i['services']} services "
              f"(SLA {', '.join(i['sla_classes'])}), {i['rekeys']} rekeys")
        print(f"  level at 00:00 {i['start_mbit']:.3f} Mbit, full from "
              f"{_hhmm(i['first_full_h'])}; full-pool reserve {i['full_reserve_h']:.2f} h")
        print(f"  minimum level {i['min_mbit']:.3f} Mbit at {_hhmm(i['t_min_mbit_h'])} "
              f"({100 * i['min_mbit'] / n['capacity_mbit']:.1f} % of B_max); "
              f"minimum reserve {i['min_reserve_h']:.2f} h at {_hhmm(i['t_min_reserve_h'])}")
        if i["outage_h"]:
            a, b = i["outage_h"]
            print(f"  refill outage {_hhmm(a)}-{_hhmm(b)}: level at end "
                  f"{i['level_at_outage_end_mbit']:.3f} Mbit, reserve at end "
                  f"{i['reserve_at_outage_end_h']:.2f} h")
            for key, label in (("below_reentry_h", "kappa*T_min"), ("below_gold_h", "T_min")):
                v = i[key]
                print(f"  reserve first below {label}: "
                      + (f"{_hhmm(v)} (5-min trace)" if v is not None else "never"))
        print(f"  demotions ({i['demoted_sessions']} sessions): "
              + (", ".join(f"{_hhmm(t)} {sid} -> {m}" for t, sid, m in i["demotions"]) or "none"))
        print(f"  re-entries: "
              + (", ".join(f"{_hhmm(t)} {sid} -> {m}" for t, sid, m in i["reentries"]) or "none"))
        print(f"  rekeys carried outside QKD: {i['non_qkd_rekeys']} of {i['rekeys']} "
              f"({100 * i['non_qkd_rekeys'] / i['rekeys']:.1f} %)")
