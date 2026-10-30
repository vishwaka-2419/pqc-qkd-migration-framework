"""Figure 5 -- empirical CDFs of the sampled rekey-control latency per adapter.

Three panels on a common logarithmic latency axis: (a) IKEv2/IPsec,
(b) MACsec, (c) OTN.  Each panel draws one dark empirical CDF (``HUE[800]``)
of all per-session latency samples of that protocol adapter in the reference
scenario, the configured per-service latency budgets as dotted ``INK3``
reference lines, each standing on its rotated value label just above the
legend (a label whose column is taken by a neighbouring line moves up one
level), and a frameless legend in the lower-right corner naming the adapter
and the number of samples ``n``.

The distribution statistics quoted in the caption are computed on *all*
samples (``protocol_stats``); only the drawn polyline is thinned to at most
``MAX_POINTS`` vertices, which is far below the pixel resolution of the
printed figure.  Run ``python3 -m figures_src.fig05_latency`` to print them.
"""
from __future__ import annotations

import numpy as np
from matplotlib.ticker import FixedLocator, NullFormatter

from hybridsim import plotstyle as ps
from figures_src._data import reference

PROTOCOLS = ("ikev2", "macsec", "otn")       # panel order (a), (b), (c)
XLIM = (0.3, 80.0)                           # ms, logarithmic
XTICKS = (0.5, 1, 2, 5, 10, 20, 50)
YLIM = (-0.015, 1.04)                        # foot of the ECDF clear of the x axis
HEIGHT_IN = 2.5
MAX_POINTS = 2000                            # vertices drawn per ECDF
LINE_GAP_PT = 2.0                            # legend top -> labels; label top -> line
LABEL_GAP_PT = 1.5                           # clearance between a label and other lines/labels


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def _runs(protocol: str) -> list:
    return [sr for sr in reference().result.service_runs
            if sr.service.protocol == protocol]


def protocol_stats(protocol: str) -> dict:
    """Latency statistics of one adapter, computed on every sample."""
    runs = _runs(protocol)
    samples = np.sort(np.concatenate(
        [np.asarray(sr.latency_samples_ms, dtype=float) for sr in runs]))
    budgets = sorted({float(sr.service.latency_budget_ms) for sr in runs})
    services_per_budget = {b: sum(1 for sr in runs
                                  if float(sr.service.latency_budget_ms) == b)
                           for b in budgets}
    # samples above the budget of the service they belong to (counted here and
    # by the simulator as deadline misses)
    exceed_own = sum(int(np.sum(np.asarray(sr.latency_samples_ms, dtype=float)
                                > sr.service.latency_budget_ms)) for sr in runs)
    misses = sum(int(sr.deadline_misses) for sr in runs)
    per_service = sorted(
        (sr.service.service_id, float(sr.service.latency_budget_ms),
         len(sr.latency_samples_ms),
         float(np.min(sr.latency_samples_ms)), float(np.median(sr.latency_samples_ms)),
         float(np.max(sr.latency_samples_ms))) for sr in runs)
    return {
        "protocol": protocol,
        "label": ps.PROTO_LABELS[protocol],
        "services": len(runs),
        "n": int(len(samples)),
        "budgets_ms": budgets,
        "services_per_budget": services_per_budget,
        "min_ms": float(samples[0]),
        "p50_ms": float(np.percentile(samples, 50)),
        "p90_ms": float(np.percentile(samples, 90)),
        "p99_ms": float(np.percentile(samples, 99)),
        "max_ms": float(samples[-1]),
        "share_within_budget": {b: float(np.mean(samples <= b)) for b in budgets},
        "exceed_own_budget": exceed_own,
        "deadline_misses": misses,
        "per_service": per_service,
        "samples": samples,
    }


def _ecdf_vertices(samples: np.ndarray, max_points: int = MAX_POINTS):
    """Thin the sorted samples to <= max_points vertices, keeping every
    plateau corner (consecutive samples more than 2 % apart)."""
    n = len(samples)
    idx = np.linspace(0, n - 1, max_points).round().astype(int)
    jumps = np.flatnonzero(samples[1:] > 1.02 * samples[:-1])
    idx = np.unique(np.concatenate([idx, jumps, jumps + 1]))
    return samples[idx], (idx + 1) / n


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def draw():
    fig = ps.figure(1.0, HEIGHT_IN)
    axes = fig.subplots(1, 3, sharey=True)
    fig.subplots_adjust(left=0.085, right=0.992, bottom=0.175, top=0.93, wspace=0.10)

    stats = [protocol_stats(p) for p in PROTOCOLS]
    legends = []
    for ax, st in zip(axes, stats):
        x, y = _ecdf_vertices(st["samples"])
        line, = ax.plot(x, y, color=ps.HUE[800], lw=1.4, ls="-", drawstyle="steps-post",
                        solid_joinstyle="round", label=st["label"], zorder=3)
        ax.set_xscale("log")
        ax.set_xlim(*XLIM)
        ax.set_ylim(*YLIM)
        ax.xaxis.set_major_locator(FixedLocator(XTICKS))
        ax.set_xticks(XTICKS, labels=[f"{t:g}" for t in XTICKS])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis="x", which="minor", length=1.5)
        # adapter name and sample count: the legend entry of the ECDF line
        # (compact, so that it stays clear of the steep OTN curve in (c))
        n_txt = f"{st['n']:,}".replace(",", "\\,")           # thin-space thousands
        legends.append(ax.legend(handles=[line], labels=[f"{st['label']}\n$n = {n_txt}$"],
                                 loc="lower right", handlelength=1.2, handletextpad=0.6,
                                 borderpad=0.25, borderaxespad=0.35, labelspacing=0.3))

    axes[0].set_ylabel("empirical CDF")
    axes[0].yaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8, 1.0]))
    axes[0].set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["0", "0.2", "0.4", "0.6", "0.8", "1.0"])

    # ---- geometry-dependent placement: measure once, then place ------------
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    px_per_pt = fig.dpi / 72.0
    # One common x label centred under the three panels (a per-panel label is
    # wider than a panel).  It is a figure text, not an axis label, so that it
    # does not widen the tight bbox of the middle panel (panel letters).
    x_mid = 0.5 * (axes[0].get_window_extent(renderer).x0
                   + axes[-1].get_window_extent(renderer).x1)
    y_top = axes[-1].xaxis.get_tightbbox(renderer).y0 - 4.0 * px_per_pt
    fx, fy = fig.transFigure.inverted().transform((x_mid, y_top))
    fig.text(fx, fy, "sampled rekey-control latency (ms)", ha="center", va="top",
             fontsize=ps.SIZE_LABEL, color=ps.INK)
    for ax, st, leg in zip(axes, stats, legends):
        axbb = ax.get_window_extent(renderer)
        lbb = leg.get_window_extent(renderer)
        tr = ax.get_xaxis_transform()
        gap = LABEL_GAP_PT * px_per_pt
        # the budget labels stand on the legend: rotated, centred on their
        # line, which starts just above its label; a label whose column is
        # taken by a neighbour moves up one level (lines of lower levels are
        # treated as obstacles there)
        y_cut = (lbb.y1 - axbb.y0 + LINE_GAP_PT * px_per_pt) / axbb.height
        probe = ax.annotate(max((f"{b:g} ms" for b in st["budgets_ms"]), key=len),
                            xy=(XLIM[0], y_cut), xycoords=tr, rotation=90,
                            ha="center", va="bottom", fontsize=ps.SIZE_ANNOT)
        pitch = (probe.get_window_extent(renderer).height + 2 * gap) / axbb.height
        probe.remove()
        placed = []                                   # (level, x0, x1, x_line) in px
        for b in st["budgets_ms"]:
            x_line = ax.transData.transform((b, 0.0))[0]
            for level in range(4):
                t = ax.annotate(f"{b:g} ms", xy=(b, y_cut + level * pitch), xycoords=tr,
                                rotation=90, ha="center", va="bottom",
                                fontsize=ps.SIZE_ANNOT, color=ps.INK2, zorder=4)
                bb = t.get_window_extent(renderer)
                ok = axbb.x0 + gap <= bb.x0 and bb.x1 <= axbb.x1 - gap
                for lv, x0, x1, xl in placed:
                    if lv == level:
                        ok &= bb.x1 + gap <= x0 or bb.x0 - gap >= x1
                    elif lv < level:                  # that line runs through this level
                        ok &= not (bb.x0 - gap < xl < bb.x1 + gap)
                if ok:
                    break
                t.remove()
            else:
                raise RuntimeError(f"no free slot for the budget label {b:g} ms")
            placed.append((level, bb.x0, bb.x1, x_line))
            y_line = (bb.y1 - axbb.y0 + LINE_GAP_PT * px_per_pt) / axbb.height
            ax.plot([b, b], [y_line, 1.0], transform=tr, color=ps.INK3, lw=0.8, ls=":",
                    zorder=2, label=f"budget {b:g} ms")

    ps.panel_labels(fig, {"a": axes[0], "b": axes[1], "c": axes[2]}, pad_pt=3.0)
    return fig


# --------------------------------------------------------------------------
# numbers for the caption
# --------------------------------------------------------------------------
def _print_stats() -> None:
    for st in (protocol_stats(p) for p in PROTOCOLS):
        print(f"{st['label']}: {st['services']} services, n = {st['n']} samples")
        print(f"  budgets (ms) and services per budget: "
              + ", ".join(f"{b:g} ms ({c})" for b, c in st['services_per_budget'].items()))
        print(f"  min {st['min_ms']:.3f}  p50 {st['p50_ms']:.3f}  p90 {st['p90_ms']:.3f}  "
              f"p99 {st['p99_ms']:.3f}  max {st['max_ms']:.3f} ms")
        print("  share of all samples within each budget: "
              + ", ".join(f"<= {b:g} ms: {s * 100:.1f} %" for b, s in st['share_within_budget'].items()))
        print(f"  samples above the budget of their own service: {st['exceed_own_budget']}"
              f" (simulator deadline misses: {st['deadline_misses']})")
        for sid, b, n, lo, med, hi in st["per_service"]:
            print(f"    {sid:16s} budget {b:4g} ms  n={n:6d}  min {lo:.3f}  median {med:.3f}  max {hi:.3f}")


if __name__ == "__main__":
    _print_stats()
