"""Figure 3 -- service-level mode mix before and after the selective QKD overlay.

Grouped horizontal bars, one row per protection mode that is assigned to at
least one of the services: the number of services in that mode in Phase 2
(PQC migration baseline, before any QKD overlay) and in Phase 3 (after the
selective QKD overlay has been planned and its routes qualified).  Single
panel, no panel letter; everything else is said in the caption.

``draw()`` returns the Figure.  Run the module as a script
(``python3 -m figures_src.fig03_mode_mix``) to print the numbers quoted in
the caption (per-mode counts and the per-service mode transitions).
"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Patch

from hybridsim import plotstyle as ps
from hybridsim.modes import ALL_MODES, QKD_MODES
from figures_src._data import reference

WIDTH, HEIGHT = 0.8, 3.0      # fraction of the text width, inches
BAR_H = 0.35                  # bar thickness as a fraction of the row pitch
BAR_GAP = 0.05                # white gap between the two bars of a row
LABEL_PAD = 0.7               # value label offset from the bar end (services)

# legend text, ScenarioOutput attribute, face colour, hatch, hatch colour
PHASES = (
    ("Phase 2: PQC migration baseline", "mix2", ps.MUTED, ps.HATCHES[1], ps.HUE[500]),
    ("Phase 3: selective QKD overlay", "mix3", ps.EMPHASIS, ps.HATCHES[0], ps.EMPHASIS),
)


def modes_with_services(mix2: dict, mix3: dict) -> list[str]:
    """Modes in manuscript order (top to bottom), keeping those with any service."""
    return [m for m in list(ALL_MODES) + ["NO_ADMISSIBLE_MODE"]
            if mix2.get(m, 0) or mix3.get(m, 0)]


def draw():
    ref = reference()
    modes = modes_with_services(ref.mix2, ref.mix3)
    total = sum(ref.mix3.values())
    assert total == sum(ref.mix2.values()), "both phases assign every service"

    fig = ps.figure(WIDTH, HEIGHT)
    ax = fig.add_subplot(111)
    ax.grid(axis="x")
    ax.grid(False, axis="y")

    rows = np.arange(len(modes), dtype=float)
    offsets = (-(BAR_H + BAR_GAP) / 2, (BAR_H + BAR_GAP) / 2)   # Phase 2 above Phase 3
    handles = []
    for (label, attr, face, hatch, hatch_colour), off in zip(PHASES, offsets):
        mix = getattr(ref, attr)
        values = [int(mix.get(m, 0)) for m in modes]
        ax.barh(rows + off, values, height=BAR_H, color=face, edgecolor=hatch_colour,
                linewidth=0, hatch=hatch, label=label)
        # value at the end of every bar; an empty bar prints "0" next to the axis
        for y, v in zip(rows + off, values):
            ax.text(v + LABEL_PAD, y, f"{v:d}", ha="left", va="center_baseline",
                    fontsize=ps.SIZE_ANNOT, color=ps.INK2)
        handles.append(Patch(facecolor=face, edgecolor=hatch_colour, linewidth=0,
                             hatch=hatch, label=label))

    ax.set_yticks(rows)
    ax.set_yticklabels([ps.MODE_LABELS[m] for m in modes])
    # first mode at the top; the margin above the first bar and below the
    # last bar equals the white gap between neighbouring rows
    half_row = BAR_H + BAR_GAP / 2
    margin = 1.0 - 2 * half_row
    ax.set_ylim(len(modes) - 1 + half_row + margin, -(half_row + margin))
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, total)
    ax.set_xticks(np.arange(0, total + 1, 10))
    ax.set_xlabel(f"services (of {total})")
    # opaque, edgeless background so that the vertical grid stops at the legend
    ax.legend(handles=handles, loc="lower right", frameon=True,
              facecolor=ps.SURFACE, edgecolor="none", framealpha=1.0)

    fig.tight_layout(pad=0.3)
    return fig


def caption_numbers() -> dict:
    """Per-mode counts and per-service transitions quoted in the caption."""
    from hybridsim.experiments import phase_decisions

    ref = reference()
    modes = modes_with_services(ref.mix2, ref.mix3)
    _, rows2 = phase_decisions(ref.links, 2, ref.params)
    mode2 = {r["service"]: r["mode"] for r in rows2}
    mode3 = {r["service"]: r["mode"] for r in ref.decisions}
    services = {s.service_id: (link, s) for link in ref.links for s in link.services}
    overlay = {link.link_id for link in ref.selected}

    transitions: dict[tuple[str, str], int] = {}
    moved = []
    for sid, m3 in mode3.items():
        key = (mode2[sid], m3)
        transitions[key] = transitions.get(key, 0) + 1
        if mode2[sid] != m3:
            link, svc = services[sid]
            moved.append((sid, link.link_id, svc.protocol, svc.assurance,
                          svc.sla_class, mode2[sid], m3))
    on_overlay = [(sid, services[sid][1].assurance, mode3[sid])
                  for sid in mode3 if services[sid][0].link_id in overlay]
    return {
        "total": sum(ref.mix3.values()),
        "modes": modes,
        "mix2": {m: ref.mix2.get(m, 0) for m in modes},
        "mix3": {m: ref.mix3.get(m, 0) for m in modes},
        "qkd_services_phase3": sum(v for m, v in ref.mix3.items() if m in QKD_MODES),
        "qkd_services_phase2": sum(v for m, v in ref.mix2.items() if m in QKD_MODES),
        "transitions": transitions,
        "moved": moved,
        "overlay_links": sorted(overlay),
        "services_on_overlay_links": on_overlay,
    }


if __name__ == "__main__":
    n = caption_numbers()
    print(f"services: {n['total']}")
    print(f"{'mode':<22}{'phase 2':>8}{'phase 3':>8}")
    for m in n["modes"]:
        print(f"{ps.MODE_LABELS[m]:<22}{n['mix2'][m]:>8}{n['mix3'][m]:>8}")
    print(f"QKD-backed services: phase 2 = {n['qkd_services_phase2']}, "
          f"phase 3 = {n['qkd_services_phase3']} "
          f"({100 * n['qkd_services_phase3'] / n['total']:.1f} % of {n['total']})")
    print("transitions (phase 2 -> phase 3):")
    for (a, b), c in sorted(n["transitions"].items(), key=lambda kv: -kv[1]):
        print(f"  {ps.MODE_LABELS[a]:<18} -> {ps.MODE_LABELS[b]:<18} {c:>3}")
    print(f"services that change mode: {len(n['moved'])}")
    for row in n["moved"]:
        print("  ", row)
    print(f"overlay links: {n['overlay_links']}")
    print(f"services on overlay links: {len(n['services_on_overlay_links'])}")
    for row in n["services_on_overlay_links"]:
        print("  ", row)
