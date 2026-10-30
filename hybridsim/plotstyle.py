"""Shared figure style for every generated figure (releases v1.1.0/v1.1.1, R1).

Design rules (IET / Wiley figure guidance):

* one hue only -- a blue ramp (``HUE``) plus neutral greys; identity is
  additionally carried by line style, marker shape or hatch so that every
  figure also reads in greyscale;
* no titles inside the figure; panels are labelled "(a)", "(b)", ... and
  everything else is said in the caption;
* figures are drawn at their final printed width (``FULL`` = text width of
  the manuscript, 160 mm) so that the point sizes below are the printed
  point sizes: axis labels 10 pt, tick labels and legends 9 pt, in-figure
  annotations 8.5 pt, panel letters 11 pt bold;
* Helvetica-compatible sans-serif (TeX Gyre Heros) with Type 42 embedding;
  the four faces are bundled in ``figures_src/fonts/`` (GUST Font License)
  and registered by ``apply_style`` so that every environment measures and
  renders text identically (the layout lint depends on the text metrics).
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# --------------------------------------------------------------------------
# colour: a single blue hue in ten steps plus neutrals
# --------------------------------------------------------------------------
HUE = {
    900: "#0b2240", 800: "#14365f", 700: "#1c4b80", 600: "#2560a1",
    500: "#3576bd", 400: "#5b92cc", 300: "#86afdb", 200: "#b2cbe8",
    100: "#d6e3f3", 50: "#edf3fa",
}
INK = "#1a1a1a"        # text, axis lines
INK2 = "#4a4a4a"       # secondary text
INK3 = "#7c7c7c"       # tertiary text, reference lines
GRID = "#dddddd"
NEUTRAL = "#c9c9c9"    # "not applicable / rejected" fills
SURFACE = "#ffffff"

# Ordered shades for up to four series (darkest = most important series).
SHADES = [HUE[800], HUE[500], HUE[300], HUE[100]]
LINESTYLES = ["-", "--", ":", "-."]
MARKERS = ["o", "s", "^", "D"]
HATCHES = ["", "////", "....", "xxxx"]
EMPHASIS = HUE[800]    # proposed scheme / reference case
MUTED = HUE[200]       # comparison cases

SEQ = [HUE[k] for k in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)]
SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", SEQ)

MODE_LABELS = {
    "TRADITIONAL_ONLY": "Traditional only",
    "PQC_ONLY": "PQC only",
    "PQT_HYBRID": "PQ/T hybrid",
    "QKD_ASSISTED": "QKD-assisted",
    "PQT_QKD_COMBINED": "PQ/T + QKD",
    "NO_ADMISSIBLE_MODE": "No admissible mode",
}
PROTO_LABELS = {"ikev2": "IKEv2/IPsec", "macsec": "MACsec", "otn": "OTN"}

# --------------------------------------------------------------------------
# geometry and typography
# --------------------------------------------------------------------------
FULL = 160 / 25.4      # printed text width of the manuscript, inches (6.30 in)
FIG_DPI = 600
FONT = "TeX Gyre Heros"
FONT_DIR = Path(__file__).resolve().parents[1] / "figures_src" / "fonts"
SIZE_LABEL = 10.0
SIZE_TICK = 9.0
SIZE_LEGEND = 9.0
SIZE_ANNOT = 8.5
SIZE_PANEL = 11.0


def register_fonts() -> list[str]:
    """Register the bundled TeX Gyre Heros faces with Matplotlib (idempotent)."""
    from matplotlib import font_manager
    paths = sorted(str(p) for p in FONT_DIR.glob("*.otf"))
    for p in paths:
        font_manager.fontManager.addfont(p)
    return paths


def apply_style() -> None:
    register_fonts()
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Nimbus Sans", "Liberation Sans", "DejaVu Sans"],
        "mathtext.fontset": "custom",
        "mathtext.rm": FONT,
        "mathtext.it": f"{FONT}:italic",
        "mathtext.bf": f"{FONT}:bold",
        "mathtext.cal": FONT,
        "mathtext.sf": FONT,
        "font.size": SIZE_TICK,
        "axes.titlesize": SIZE_LABEL,       # titles are not used; kept sane
        "axes.labelsize": SIZE_LABEL,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "axes.axisbelow": True,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": SIZE_TICK,
        "ytick.labelsize": SIZE_TICK,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "legend.fontsize": SIZE_LEGEND,
        "legend.frameon": False,
        "legend.handlelength": 2.2,
        "legend.borderaxespad": 0.3,
        "lines.linewidth": 1.4,
        "lines.markersize": 5,
        "hatch.linewidth": 0.5,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def figure(width: float = 1.0, height_in: float = 3.2, **kw):
    """Create a figure ``width`` x FULL inches wide and ``height_in`` tall."""
    return plt.figure(figsize=(width * FULL, height_in), **kw)


def panel_labels(fig, mapping: dict, pad_pt: float = 2.0) -> None:
    """Place bold "(a)", "(b)", ... at the top-left corner of each panel.

    ``mapping`` maps a letter to an Axes (or to a list of Axes whose joint
    extent defines the panel). The letter is placed just outside the tight
    bounding box of the panel (which includes tick and axis labels), so it
    never collides with the panel content. Call after the layout is final
    (after ``tight_layout``/``subplots_adjust``) and before ``save``.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    pad = pad_pt / 72 * fig.dpi
    for letter, axes in mapping.items():
        axes = axes if isinstance(axes, (list, tuple)) else [axes]
        boxes = [a.get_tightbbox(renderer) for a in axes]
        x0 = min(b.x0 for b in boxes) - pad
        y1 = max(b.y1 for b in boxes) + pad
        fx, fy = inv.transform((x0, y1))
        fig.text(fx, fy, f"({letter})", fontsize=SIZE_PANEL, fontweight="bold",
                 ha="left", va="bottom", color=INK, gid="panel-label")


def save(fig, path_stem, dpi: int = FIG_DPI, tiff: bool = True) -> None:
    """Write <stem>.png (600 dpi), <stem>.pdf (vector) and <stem>.tiff (LZW)."""
    stem = Path(str(path_stem))
    fig.savefig(stem.with_suffix(".png"), dpi=dpi, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.03)
    if tiff:
        from PIL import Image
        with Image.open(stem.with_suffix(".png")) as im:
            im.convert("RGB").save(stem.with_suffix(".tiff"), compression="tiff_lzw",
                                   dpi=(dpi, dpi))
    plt.close(fig)
