"""Every matplotlib figure of the manuscript must pass the layout lint:
no titles, no text overlapping data or other text, no text below 8 pt."""
import importlib

import pytest

from hybridsim import plotstyle as ps
from hybridsim.figcheck import lint

MODULES = ["fig02_envelope", "fig03_mode_mix", "fig04_pool", "fig05_latency",
           "fig06_cost", "fig07_oat", "fig08_grid", "fig09_baselines", "fig10_seeds"]


@pytest.mark.parametrize("module", MODULES)
def test_figure_passes_layout_lint(module):
    ps.apply_style()
    fig = importlib.import_module(f"figures_src.{module}").draw()
    assert lint(fig) == []


def test_palette_is_single_hue():
    import colorsys
    hues = set()
    for hexcode in ps.HUE.values():
        r, g, b = (int(hexcode[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hues.add(round(colorsys.rgb_to_hls(r, g, b)[0], 2))
    assert max(hues) - min(hues) < 0.03
