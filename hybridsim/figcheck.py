"""Deterministic layout lint for generated figures.

``lint(fig)`` renders the figure once and reports, in display pixels:

* text that overlaps other text (including tick labels);
* text or legends that overlap plotted lines, markers, bars or filled areas;
* text that spills into a neighbouring panel;
* titles set on any Axes (the manuscript style allows no in-figure titles);
* text smaller than the minimum printed size.

Overlaps that are intentional (a value printed inside a heat-map cell, a
label inside a wide bar) are declared by giving the artist
``gid="allow-overlap"``. Background patches (``axvspan`` etc. with alpha
below 0.5, or facecolor "none") are ignored.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
from matplotlib.collections import PathCollection, PolyCollection, LineCollection
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.text import Text, Annotation
from matplotlib.transforms import Bbox

MIN_FONT_PT = 8.0
ALLOW = "allow-overlap"


def _visible_texts(fig):
    out = []
    for ax in fig.axes:
        for t in ax.texts:
            out.append((ax, t))
        for axis in (ax.xaxis, ax.yaxis):
            for t in axis.get_ticklabels(which="both"):
                out.append((ax, t))
            lab = axis.get_label()
            if lab.get_text():
                out.append((ax, lab))
        leg = ax.get_legend()
        if leg is not None:
            for t in leg.get_texts():
                t._lint_legend = True
                out.append((ax, t))
    for t in fig.texts:
        out.append((None, t))
    return [(ax, t) for ax, t in out
            if isinstance(t, Text) and t.get_visible() and t.get_text().strip()]


def _bbox(artist, renderer):
    try:
        bb = artist.get_window_extent(renderer)
    except Exception:
        return None
    if bb is None or not np.all(np.isfinite([bb.x0, bb.y0, bb.x1, bb.y1])):
        return None
    if bb.width <= 0 or bb.height <= 0:
        return None
    return bb


def _shrink(bb, px):
    return Bbox.from_extents(bb.x0 + px, bb.y0 + px, bb.x1 - px, bb.y1 - px)


def _densify(pts, step=2.0):
    pts = np.asarray(pts, float)
    pts = pts[np.all(np.isfinite(pts), axis=1)]
    if len(pts) < 2:
        return pts
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.hypot(*(b - a)) / step))
        out.append(np.linspace(a, b, n + 1)[1:])
    return np.vstack(out)


def _data_points(ax, renderer):
    """Display-space points of every foreground data artist, with a radius."""
    pts = []
    for ln in ax.lines:
        if not ln.get_visible() or ln.get_gid() == ALLOW:
            continue
        xy = ln.get_xydata()
        if len(xy) == 0:
            continue
        disp = ln.get_transform().transform(xy)
        disp = disp[np.all(np.isfinite(disp), axis=1)]
        if ln.get_linestyle() not in ("None", "none", "", " "):
            disp = _densify(disp)
        r = 0.5 * ln.get_linewidth() * ax.figure.dpi / 72
        if ln.get_marker() not in ("None", "none", "", " ", None):
            r = max(r, 0.5 * ln.get_markersize() * ax.figure.dpi / 72)
        pts.append((disp, r, f"line '{ln.get_label()}'"))
    for col in ax.collections:
        if not col.get_visible() or col.get_gid() == ALLOW:
            continue
        if isinstance(col, PathCollection):
            off = col.get_offsets()
            if len(off) == 0:
                continue
            disp = col.get_offset_transform().transform(off)
            sizes = col.get_sizes()
            r = float(np.sqrt(sizes.max()) / 2 * ax.figure.dpi / 72) if len(sizes) else 3
            pts.append((disp, r, f"scatter '{col.get_label()}'"))
        elif isinstance(col, LineCollection):
            for p in col.get_paths():
                disp = col.get_transform().transform(p.vertices)
                pts.append((_densify(disp), 1.0, "line collection"))
        elif isinstance(col, PolyCollection):
            if col.get_alpha() is not None and col.get_alpha() < 0.5:
                continue
            for p in col.get_paths():
                disp = col.get_transform().transform(p.vertices)
                pts.append((_densify(disp), 1.0, "filled area edge"))
    return pts


def _foreground_patches(ax, renderer):
    out = []
    for p in ax.patches:
        if not p.get_visible() or p.get_gid() == ALLOW:
            continue
        alpha = p.get_alpha()
        fc = p.get_facecolor()
        if (alpha is not None and alpha < 0.5) or (len(fc) == 4 and fc[3] < 0.5):
            continue
        if not p.get_fill() and p.get_linewidth() == 0:
            continue
        bb = _bbox(p, renderer)
        if bb is None or bb.width < 1 or bb.height < 1:
            continue
        kind = type(p).__name__
        out.append((bb, kind))
    return out


def lint(fig, min_font_pt: float = MIN_FONT_PT) -> list[str]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    issues: list[str] = []

    # 1. titles
    for i, ax in enumerate(fig.axes):
        if ax.get_title():
            issues.append(f"axes {i}: has a title '{ax.get_title()}' (titles are not allowed)")
    if fig._suptitle is not None and fig._suptitle.get_text():
        issues.append("figure has a suptitle (not allowed)")

    texts = _visible_texts(fig)
    boxes = []
    for ax, t in texts:
        bb = _bbox(t, renderer)
        if bb is None:
            continue
        boxes.append((ax, t, bb))
        # 2. font size
        if t.get_fontsize() < min_font_pt - 1e-6 and t.get_gid() != ALLOW:
            issues.append(f"text '{t.get_text()[:40]}' is {t.get_fontsize():.1f} pt (< {min_font_pt} pt)")

    # 3. text vs text (legend entries are covered by the legend box check)
    boxes = [(ax, t, bb) for ax, t, bb in boxes if not getattr(t, "_lint_legend", False)]
    for (ax1, t1, b1), (ax2, t2, b2) in combinations(boxes, 2):
        if t1.get_gid() == ALLOW or t2.get_gid() == ALLOW:
            continue
        if _shrink(b1, 1).overlaps(_shrink(b2, 1)):
            issues.append(f"text overlap: '{t1.get_text()[:40]}' <> '{t2.get_text()[:40]}'")

    # 4. text vs data; text spilling into other axes
    ax_boxes = {ax: ax.get_window_extent(renderer) for ax in fig.axes}
    for ax, t, bb in boxes:
        if t.get_gid() == ALLOW:
            continue
        label = t.get_text()[:40]
        for other, obb in ax_boxes.items():
            if other is ax or ax is None:
                continue
            if _shrink(bb, 1).overlaps(_shrink(obb, 1)) and other is not getattr(ax, "_lint_twin", None):
                if ax is not None and other in getattr(ax, "_lint_siblings", ()):
                    continue
                issues.append(f"text '{label}' spills into another panel")
                break
        for target in fig.axes:
            tb = ax_boxes[target]
            if not bb.overlaps(tb):
                continue
            for disp, r, what in _data_points(target, renderer):
                ext = Bbox.from_extents(bb.x0 - r, bb.y0 - r, bb.x1 + r, bb.y1 + r)
                inside = (disp[:, 0] > ext.x0) & (disp[:, 0] < ext.x1) & \
                         (disp[:, 1] > ext.y0) & (disp[:, 1] < ext.y1)
                if inside.any():
                    issues.append(f"text '{label}' overlaps {what}")
                    break
            for pbb, kind in _foreground_patches(target, renderer):
                if _shrink(bb, 1).overlaps(_shrink(pbb, 1)):
                    issues.append(f"text '{label}' overlaps a {kind}")
                    break

    # 5. legends vs data
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None or leg.get_gid() == ALLOW:
            continue
        bb = _bbox(leg, renderer)
        if bb is None:
            continue
        for target in fig.axes:
            if not bb.overlaps(ax_boxes[target]):
                continue
            for disp, r, what in _data_points(target, renderer):
                ext = Bbox.from_extents(bb.x0 - r, bb.y0 - r, bb.x1 + r, bb.y1 + r)
                inside = (disp[:, 0] > ext.x0) & (disp[:, 0] < ext.x1) & \
                         (disp[:, 1] > ext.y0) & (disp[:, 1] < ext.y1)
                if inside.any():
                    issues.append(f"legend overlaps {what}")
                    break
            for pbb, kind in _foreground_patches(target, renderer):
                if _shrink(bb, 1).overlaps(_shrink(pbb, 1)):
                    issues.append(f"legend overlaps a {kind}")
                    break

    # de-duplicate, keep order
    seen, out = set(), []
    for s in issues:
        if s not in seen:
            seen.add(s); out.append(s)
    return out
