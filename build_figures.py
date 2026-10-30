"""Build the manuscript figures.

    python3 build_figures.py            # all figures
    python3 build_figures.py 2 7 GA     # a subset

Matplotlib figures live in ``figures_src/figNN_*.py`` and expose
``draw() -> matplotlib.figure.Figure``; the layout lint in
``hybridsim.figcheck`` must pass (or the build fails). Schematics live in
``figures_src/*.tex`` (TikZ) and are compiled with pdflatex, rasterised at
600 dpi with pdftoppm and converted to LZW TIFF.
"""
from __future__ import annotations
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
LINT = FIG / "lint"
SRC = ROOT / "figures_src"
FIG.mkdir(exist_ok=True)
LINT.mkdir(exist_ok=True)

# figure id -> (module or tex stem, output stem)
REGISTRY = {
    "1": ("fig01_architecture.tex", "Figure_1"),
    "2": ("fig02_envelope", "Figure_2"),
    "3": ("fig03_mode_mix", "Figure_3"),
    "4": ("fig04_pool", "Figure_4"),
    "5": ("fig05_latency", "Figure_5"),
    "6": ("fig06_cost", "Figure_6"),
    "7": ("fig07_oat", "Figure_7"),
    "8": ("fig08_grid", "Figure_8"),
    "9": ("fig09_baselines", "Figure_9"),
    "10": ("fig10_seeds", "Figure_10"),
    "GA": ("graphical_abstract.tex", "Graphical_Abstract"),
}


def check_ga_values(src: Path) -> None:
    """The graphical abstract is a TikZ file with literal result values;
    refuse to build it if they no longer match results/summary.csv."""
    import csv
    with open(ROOT / "results" / "summary.csv", newline="") as fh:
        m = {}
        for row in csv.DictReader(fh):
            try:
                m[row["metric"]] = float(row["value"])
            except ValueError:
                pass
    expected = [f"{m['qkd_overlay_links']:.0f} of {m['links_total']:.0f}",
                f"\\num{{{m['physical_qkd_hops']:.0f}}} physical hops",
                f"\\num{{{m['trusted_sites']:.0f}}} trusted sites",
                f"\\num{{{m['qkd_backed_rekey_pct']:.1f}\\,\\%}}",
                f"\\num{{{m['hybrid_premium_5y_npv_kEUR'] / 1000:.2f}\\,MEUR}}"]
    missing = [e for e in expected if e not in src.read_text()]
    if missing:
        raise SystemExit(f"{src.name}: result literals differ from results/summary.csv: {missing}")


def build_tikz(tex_name: str, stem: str) -> None:
    src = SRC / tex_name
    if stem == "Graphical_Abstract":
        check_ga_values(src)
    work = FIG / ".tikz"
    work.mkdir(exist_ok=True)
    for _ in range(2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            "-output-directory", str(work), str(src)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            log = (work / src.with_suffix(".log").name)
            tail = log.read_text(errors="replace")[-3000:] if log.exists() else r.stdout[-3000:]
            raise SystemExit(f"pdflatex failed for {tex_name}:\n{tail}")
    pdf = work / src.with_suffix(".pdf").name
    shutil.copy(pdf, FIG / f"{stem}.pdf")
    subprocess.run(["pdftoppm", "-r", "600", "-png", "-singlefile", str(pdf),
                    str(FIG / stem)], check=True)
    from PIL import Image
    with Image.open(FIG / f"{stem}.png") as im:
        im.convert("RGB").save(FIG / f"{stem}.tiff", compression="tiff_lzw", dpi=(600, 600))
    print(f"[ok] {stem} (tikz)")


def build_mpl(module: str, stem: str, strict: bool = True) -> list[str]:
    from hybridsim import plotstyle as ps
    from hybridsim.figcheck import lint
    ps.apply_style()
    mod = importlib.import_module(f"figures_src.{module}")
    fig = mod.draw()
    issues = lint(fig)
    (LINT / f"{stem}.txt").write_text("\n".join(issues) + ("\n" if issues else ""))
    ps.save(fig, FIG / stem)
    if issues:
        print(f"[lint] {stem}: {len(issues)} issue(s)")
        for s in issues:
            print("   -", s)
        if strict:
            raise SystemExit(f"{stem}: layout lint failed")
    else:
        print(f"[ok] {stem}")
    return issues


def build(ids=None, strict: bool = True) -> None:
    ids = list(ids) if ids else list(REGISTRY)
    for i in ids:
        src, stem = REGISTRY[str(i)]
        if src.endswith(".tex"):
            build_tikz(src, stem)
        else:
            build_mpl(src, stem, strict=strict)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args or None, strict="--lenient" not in sys.argv)
