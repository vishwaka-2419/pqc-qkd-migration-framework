"""Figure 8 -- joint sensitivity to the designed hop limit and the trusted-node
policy limit (two heat maps).

(a) physical QKD hops of the selected overlay, with the number of overlaid
    logical links printed in brackets on a second line;
(b) five-year assurance premium (NPV, MEUR).

Data: ``results/sensitivity/hop_limit_grid.csv`` through
``figures_src._data.sensitivity('hop_limit_grid')``; the reference
configuration is ``DEFAULT.max_hop_km`` x ``DEFAULT.trusted_node_limit``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from hybridsim import plotstyle as ps
from figures_src._data import sensitivity, DEFAULT

# ---------------------------------------------------------------- geometry (in)
WIDTH = 1.0                 # fraction of the text width
HEIGHT_IN = 3.8             # total figure height
LEFT_IN = 0.55              # y label + y tick labels of panel (a)
MID_IN = 0.85               # gap between the heat maps (holds y label + ticks of (b))
RIGHT_IN = 0.06
TOP_IN = 0.27               # room for the panel letters
BELOW_IN = 1.08             # x ticks + x label + colour bar + its ticks + its label
CB_DROP_IN = 0.55           # heat-map bottom edge -> colour-bar top edge
CB_H_IN = 0.10              # colour-bar thickness

X_LABEL = "trusted-node policy limit"
Y_LABEL = "designed hop limit (km)"


# ------------------------------------------------------------------- data
def load() -> dict:
    """Pivot the grid sweep into hop-limit x policy-limit matrices."""
    df = sensitivity("hop_limit_grid").copy()
    parts = df["value"].astype(str).str.split("|", expand=True)
    df["hop"] = parts[0].astype(int)
    df["limit"] = parts[1].astype(int)
    hops = df.pivot(index="hop", columns="limit", values="physical_qkd_hops").astype(int)
    links = df.pivot(index="hop", columns="limit", values="qkd_overlay_links").astype(int)
    prem = df.pivot(index="hop", columns="limit", values="premium_npv_kEUR") / 1000.0  # MEUR
    hops = hops.sort_index().sort_index(axis=1)
    links = links.loc[hops.index, hops.columns]
    prem = prem.loc[hops.index, hops.columns]
    ref = (int(round(DEFAULT.max_hop_km)), int(DEFAULT.trusted_node_limit))
    if ref[0] not in hops.index or ref[1] not in hops.columns:
        raise ValueError(f"reference configuration {ref} is not in the grid")
    return {"hops": hops, "links": links, "prem": prem, "ref": ref}


# ------------------------------------------------------------------ helpers
def _rel_luminance(rgba) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgba[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _text_colour(cell_rgba) -> str:
    """Ink on light cells, white on dark cells (whichever contrasts more)."""
    lum = _rel_luminance(cell_rgba)
    ink = _rel_luminance(
        tuple(int(ps.INK[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    contrast_ink = (lum + 0.05) / (ink + 0.05)
    contrast_white = 1.05 / (lum + 0.05)
    return "white" if contrast_white > contrast_ink else ps.INK


def _heatmap(fig, ax, cax, mat: pd.DataFrame, vmax: float, cb_label: str,
             cb_ticks, cell_text, ref: tuple) -> None:
    rows, cols = list(mat.index), list(mat.columns)
    # vector cells (crisp in the PDF, unlike an up-scaled raster image) with
    # thin white separators; the first row (smallest hop limit) is at the bottom
    xe = np.arange(-0.5, len(cols) + 0.5, 1.0)
    ye = np.arange(-0.5, len(rows) + 0.5, 1.0)
    im = ax.pcolormesh(xe, ye, mat.values, cmap=ps.SEQ_CMAP, vmin=0, vmax=vmax,
                       shading="flat", edgecolors="white", linewidth=0.6,
                       antialiased=True, zorder=1)
    # frame on all four sides (drawn above the mesh, so it covers the white
    # outer edges), no background grid
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(0.7)
        s.set_color(ps.INK)
        s.set_zorder(4)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([str(c) for c in cols])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([str(r) for r in rows])
    ax.set_xlim(-0.5, len(cols) - 0.5)
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)
    # values printed inside the cells
    for i, r in enumerate(rows):
        for k, c in enumerate(cols):
            v = float(mat.loc[r, c])
            colour = _text_colour(im.cmap(im.norm(v)))
            ax.text(k, i, cell_text(r, c), ha="center", va="center",
                    fontsize=ps.SIZE_ANNOT, color=colour, linespacing=1.05,
                    gid="allow-overlap", zorder=3)
    # reference configuration
    ri, rk = rows.index(ref[0]), cols.index(ref[1])
    ax.add_patch(Rectangle((rk - 0.5, ri - 0.5), 1.0, 1.0, fill=False,
                           edgecolor=ps.INK, linewidth=1.4, zorder=5))
    # colour bar
    cb = fig.colorbar(im, cax=cax, orientation="horizontal", ticks=cb_ticks)
    cb.set_label(cb_label)
    cb.outline.set_linewidth(0.7)
    cb.outline.set_edgecolor(ps.INK)
    cax.grid(False)
    cax.tick_params(length=3, width=0.7, labelsize=ps.SIZE_TICK)


# --------------------------------------------------------------------- draw
def draw():
    d = load()
    hops, links, prem, ref = d["hops"], d["links"], d["prem"], d["ref"]

    fig = ps.figure(WIDTH, HEIGHT_IN)
    W, H = fig.get_size_inches()
    panel_w = (W - LEFT_IN - MID_IN - RIGHT_IN) / 2.0
    panel_h = H - TOP_IN - BELOW_IN
    axes, caxes = [], []
    for j in range(2):
        x0 = LEFT_IN + j * (panel_w + MID_IN)
        axes.append(fig.add_axes([x0 / W, BELOW_IN / H, panel_w / W, panel_h / H]))
        caxes.append(fig.add_axes([x0 / W, (BELOW_IN - CB_DROP_IN - CB_H_IN) / H,
                                   panel_w / W, CB_H_IN / H]))

    vmax_hops = float(hops.values.max())
    _heatmap(fig, axes[0], caxes[0], hops.astype(float), vmax_hops,
             "physical QKD hops", np.arange(0, vmax_hops + 1e-9, 5),
             lambda r, c: f"{int(hops.loc[r, c])}\n({int(links.loc[r, c])})", ref)

    vmax_prem = float(np.ceil(prem.values.max()))
    _heatmap(fig, axes[1], caxes[1], prem, vmax_prem,
             "assurance premium (MEUR)", np.arange(0, vmax_prem + 1e-9, 1),
             lambda r, c: f"{prem.loc[r, c]:.1f}", ref)

    ps.panel_labels(fig, {"a": axes[0], "b": axes[1]})
    return fig


# ------------------------------------------------------------- caption numbers
def caption_numbers() -> dict:
    d = load()
    hops, links, prem, ref = d["hops"], d["links"], d["prem"], d["ref"]
    out = {
        "rows_hop_km": list(hops.index),
        "cols_limit": list(hops.columns),
        "reference": ref,
        "ref_hops": int(hops.loc[ref]),
        "ref_links": int(links.loc[ref]),
        "ref_premium_MEUR": round(float(prem.loc[ref]), 1),
        "hops_min": int(hops.values.min()), "hops_max": int(hops.values.max()),
        "links_min": int(links.values.min()), "links_max": int(links.values.max()),
        "premium_min_MEUR": round(float(prem.values.min()), 1),
        "premium_max_MEUR": round(float(prem.values.max()), 1),
    }
    # the cell with the largest footprint
    i, k = np.unravel_index(np.argmax(hops.values), hops.shape)
    out["max_cell"] = (int(hops.index[i]), int(hops.columns[k]),
                       int(hops.values[i, k]), int(links.values[i, k]),
                       round(float(prem.values[i, k]), 1))
    # direct-span-only plateau: the cells whose overlay uses no trusted node
    # are the cells where hops == links (one hop per link)
    direct = hops.values == links.values
    out["direct_only_cells"] = int(direct.sum())
    out["direct_only_hops"] = sorted({int(v) for v in hops.values[direct]})
    out["direct_only_premium_MEUR"] = sorted({round(float(v), 1) for v in prem.values[direct]})
    # full overlay (all links that can ever qualify)
    full = links.values == links.values.max()
    out["full_overlay_links"] = int(links.values.max())
    out["full_overlay_hops_range"] = (int(hops.values[full].min()), int(hops.values[full].max()))
    out["full_overlay_premium_range_MEUR"] = (round(float(prem.values[full].min()), 1),
                                              round(float(prem.values[full].max()), 1))
    # along the reference row / column
    out["ref_row_hops"] = [int(v) for v in hops.loc[ref[0]]]
    out["ref_row_links"] = [int(v) for v in links.loc[ref[0]]]
    out["ref_row_premium_MEUR"] = [round(float(v), 1) for v in prem.loc[ref[0]]]
    out["ref_col_hops"] = [int(v) for v in hops[ref[1]]]
    out["ref_col_links"] = [int(v) for v in links[ref[1]]]
    out["ref_col_premium_MEUR"] = [round(float(v), 1) for v in prem[ref[1]]]
    return out


if __name__ == "__main__":
    for k, v in caption_numbers().items():
        print(f"{k}: {v}")
