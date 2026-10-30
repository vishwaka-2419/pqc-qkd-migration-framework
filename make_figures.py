"""Figures 7-10 from the CSV output of ``run_sensitivity.py``.

The figure code lives in ``figures_src/`` (one module per figure) and is
built, linted and saved by ``build_figures.py``; this entry point is kept for
the commands quoted in the manuscript.
"""
from build_figures import build

if __name__ == "__main__":
    build(["7", "8", "9", "10"])
    print("[done] Figures 7-10 written to figures/")
