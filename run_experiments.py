"""Generate the reference simulation results, tables, and figures."""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from hybridsim.modes import ALL_MODES, QKD_MODES
from hybridsim.policy import RuntimeState, decide
from hybridsim.qkd import plan_qkd_link, skr_point_to_point
from hybridsim.selection import deploy_selective_qkd
from hybridsim.simulate import simulate, link_qkd_demand_bps
from hybridsim.tco import five_year_tco
from hybridsim.topology import build, iter_services, Capabilities
from hybridsim.qkd import QKDRouteResources

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
RES = ROOT / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

# Wiley requests the highest practical quality. 600 dpi PNGs are used for
# all line-art figures; each remains below the journal's 10 MB per-file guidance.
FIG_DPI = 600

LABELS = {
    "TRADITIONAL_ONLY": "Traditional only",
    "PQC_ONLY": "PQC only",
    "PQT_HYBRID": "PQ/T hybrid",
    "QKD_ASSISTED": "QKD-assisted",
    "PQT_QKD_COMBINED": "PQ/T + QKD",
}


def phase_inventory(links):
    rows = []
    for link, service in iter_services(links):
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        rows.append({
            "link": link.link_id,
            "service": service.service_id,
            "protocol": service.protocol,
            "sessions": service.sessions,
            "km": round(link.distance_km, 1),
            "sla": service.sla_class,
            "secrecy_yr": service.secrecy_lifetime_yr,
            "migration_yr": service.migration_lead_time_yr,
            "quantum_horizon_yr": service.quantum_horizon_yr,
            "mosca_margin_yr": service.mosca_margin_yr,
            "hndl_exposed": service.hndl_exposed,
            "assurance": service.assurance,
            "qkd_feasible": plan.feasible,
            "qkd_reason": plan.reason,
            "qkd_hops": plan.n_physical_hops,
            "trusted_nodes": plan.n_trusted_nodes,
        })
    with (RES / "inventory_services.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    return rows


def phase_decisions(links, phase):
    rows = []
    mix = {}
    for link, service in iter_services(links):
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        reserve = float("inf") if link.qkd_deployed and plan.feasible else 0.0
        d = decide(link, service, RuntimeState(phase, plan, link.qkd_deployed,
                                                reserve, True))
        mix[d.mode or "NO_ADMISSIBLE_MODE"] = mix.get(d.mode or "NO_ADMISSIBLE_MODE", 0) + 1
        rows.append({
            "phase": phase,
            "link": link.link_id,
            "service": service.service_id,
            "protocol": service.protocol,
            "mode": d.mode,
            "fallback_chain": ">".join(d.fallback_chain),
            "estimated_latency_ms": round(d.estimated_latency_ms, 3),
            "rationale": d.rationale,
        })
    return mix, rows


def fig_architecture():
    """Render the layered architecture with arrows confined to inter-layer gaps."""
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.set_xlim(0, 10.6); ax.set_ylim(0, 10); ax.axis("off")
    layers = [
        (8.25, "Policy and orchestration",
         "service context, Mosca margin, SLA, reserve-time forecast, downgrade policy"),
        (6.05, "Key-source layer",
         "ML-KEM / PQ-T hybrid   |   paired QKD KME domain model with key IDs"),
        (3.85, "Protocol adapters",
         "IKEv2 CREATE_CHILD_SA   |   MACsec/MKA abstraction   |   OTN encryptor abstraction"),
        (1.65, "Encrypted services",
         "IPsec tunnels   |   Ethernet secure associations   |   optical channels"),
    ]
    box_x, box_w, box_h = 0.55, 8.95, 1.42
    box_edges = []
    for y, title, subtitle in layers:
        lower = y - box_h / 2
        upper = y + box_h / 2
        box_edges.append((lower, upper))
        box = FancyBboxPatch(
            (box_x, lower), box_w, box_h,
            boxstyle="round,pad=0.035,rounding_size=0.08",
            linewidth=1.25, facecolor="white"
        )
        ax.add_patch(box)
        ax.text(0.88, y + 0.25, title, fontsize=11.2,
                fontweight="bold", va="center")
        ax.text(0.88, y - 0.30, subtitle, fontsize=8.6, va="center")

    # Bidirectional arrows sit entirely in the white gaps between adjacent boxes.
    for i in range(len(box_edges) - 1):
        upper_box_lower = box_edges[i][0]
        lower_box_upper = box_edges[i + 1][1]
        ax.annotate(
            "", xy=(5.02, lower_box_upper + 0.06),
            xytext=(5.02, upper_box_lower - 0.06),
            arrowprops=dict(arrowstyle="<->", lw=1.25,
                            shrinkA=0, shrinkB=0)
        )

    ax.text(9.72, 5.0, "bidirectional\ncontrol + telemetry",
            fontsize=8.2, ha="left", va="center")
    fig.subplots_adjust(left=0.025, right=0.98, bottom=0.04, top=0.97)
    fig.savefig(FIG / "Figure_1.png", dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(FIG / "Figure_1.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_qkd_routes(links):
    """Plot feasible rates and route-qualification outcomes without label collisions."""
    d = np.linspace(1, 220, 500)
    r = np.array([skr_point_to_point(x) for x in d])
    fig, ax = plt.subplots(figsize=(9.4, 4.9))
    ax.semilogy(d, np.where(r > 0, r, np.nan), lw=2,
                label="direct-span attenuation envelope")

    dci_points = []
    feasible_core = []
    rejected_points = []
    rejected_rows = []
    reject_y = {"core-1": 78.0, "core-2": 72.0,
                "core-4": 66.0, "core-5": 61.0}

    for link in links:
        if link.kind not in {"dci", "core"}:
            continue
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        if link.kind == "dci":
            dci_points.append((link.distance_km, plan.skr_bps, link.link_id))
            continue

        if plan.feasible:
            feasible_core.append((link.distance_km, plan.skr_bps,
                                  link.link_id, plan.n_physical_hops))
        else:
            y = reject_y.get(link.link_id, 65.0)
            rejected_points.append((link.distance_km, y))
            reason = plan.reason.replace("trusted-node policy limit exceeded",
                                         "trusted-node policy limit")
            reason = reason.replace("insufficient approved trusted sites",
                                    "insufficient trusted sites")
            rejected_rows.append((link.link_id, link.distance_km,
                                  plan.n_physical_hops, reason))

    if dci_points:
        ax.scatter([x for x, _, _ in dci_points],
                   [y for _, y, _ in dci_points],
                   marker="o", s=44, label="feasible direct DCI routes", zorder=4)
        x_mid = sum(x for x, _, _ in dci_points) / len(dci_points)
        y_mid = sum(y for _, y, _ in dci_points) / len(dci_points)
        ax.annotate("dci-0 / dci-1\ndirect spans", (x_mid, y_mid),
                    xytext=(18, 14), textcoords="offset points", fontsize=7.2,
                    ha="left", va="bottom",
                    arrowprops=dict(arrowstyle="-", lw=0.7))

    if feasible_core:
        ax.scatter([x for x, _, _, _ in feasible_core],
                   [y for _, y, _, _ in feasible_core],
                   marker="s", s=52, label="feasible trusted-node core routes",
                   zorder=4)
        for x, y, link_id, hops in feasible_core:
            offset = (9, -18) if link_id == "core-0" else (-42, -28)
            ax.annotate(f"{link_id}\n{hops} hops", (x, y), xytext=offset,
                        textcoords="offset points", fontsize=7.4,
                        ha="left", va="bottom" if offset[1] > 0 else "top",
                        arrowprops=dict(arrowstyle="-", lw=0.7))

    if rejected_points:
        ax.scatter([x for x, _ in rejected_points],
                   [y for _, y in rejected_points],
                   marker="x", s=52, label="route rejected by non-rate constraints",
                   zorder=4)

    ax.axhspan(55, 100, alpha=0.06, zorder=0)
    ax.axhline(100, ls=":", lw=1.1, label="planning floor")
    ax.text(4, 63, "qualification-failure band\n(rate not evaluated)",
            fontsize=7.2, va="bottom")
    ax.set_xlim(-10, 455)
    ax.set_ylim(52, 1.6e6)
    ax.set_xlabel("route length (km)")
    ax.set_ylabel("planning-envelope secret-key rate (bit/s)")
    ax.set_title("QKD route planning with optical-path and trusted-site constraints")
    ax.grid(alpha=.28)
    ax.legend(fontsize=7.7, loc="upper right", frameon=True)
    fig.subplots_adjust(left=0.09, right=0.70, bottom=0.17, top=0.88)

    # A compact qualification table carries long failure labels outside the plot.
    fig.text(0.73, 0.83, "Rejected long-haul routes", fontsize=9.2,
             fontweight="bold", ha="left")
    fig.text(0.73, 0.78, "route     km   hops   reason", fontsize=7.5,
             family="monospace", ha="left")
    y_text = 0.73
    for route, km, hops, reason in rejected_rows:
        fig.text(0.73, y_text, f"{route:<8} {km:>4.0f}  {hops:>4}   {reason}",
                 fontsize=7.1, family="monospace", ha="left")
        y_text -= 0.075
    fig.text(0.73, 0.33,
             "Feasible core routes\n"
             "core-0: 331 km, 5 hops\n"
             "core-3: 300 km, 4 hops",
             fontsize=7.4, ha="left", linespacing=1.35)
    fig.text(0.73, 0.16,
             "Crosses below the planning floor denote\n"
             "qualification failure, not a measured SKR.",
             fontsize=7.0, ha="left", style="italic")

    fig.savefig(FIG / "Figure_2.png", dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(FIG / "Figure_2.pdf", bbox_inches="tight")
    plt.close(fig)

def fig_mode_mix(mix2, mix3):
    modes = list(ALL_MODES) + ["NO_ADMISSIBLE_MODE"]
    x = np.arange(len(modes)); width = 0.38
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.bar(x-width/2, [mix2.get(m, 0) for m in modes], width,
           label="Phase 2: PQC migration baseline")
    ax.bar(x+width/2, [mix3.get(m, 0) for m in modes], width,
           label="Phase 3: selective QKD overlay")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS.get(m, "No admissible") for m in modes],
                       rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("services")
    ax.set_title("Service-level mode assignments")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3); fig.tight_layout()
    fig.savefig(FIG / "Figure_3.png", dpi=FIG_DPI)
    fig.savefig(FIG / "Figure_3.pdf")
    plt.close(fig)


def fig_pool(result, outages, trace_ids):
    fig, ax = plt.subplots(figsize=(7.3, 4.4))
    for lr in result.link_runs:
        if lr.link.link_id not in trace_ids or not lr.pool_trace:
            continue
        t = [x[0]/3600 for x in lr.pool_trace]
        level = [x[1]/1e6 for x in lr.pool_trace]
        ax.plot(t, level, lw=1.7, label=lr.link.link_id)
        if lr.link.link_id in outages:
            a, b = outages[lr.link.link_id]
            ax.axvspan(a/3600, b/3600, alpha=.10,
                       label=f"{lr.link.link_id} QKD outage")
    ax.set_xlabel("time (h)")
    ax.set_ylabel("paired-KME pool level (Mbit)")
    ax.set_title("Key-pool dynamics and link-specific QKD outages")
    ax.grid(alpha=.3); ax.legend(fontsize=7); fig.tight_layout()
    fig.savefig(FIG / "Figure_4.png", dpi=FIG_DPI)
    fig.savefig(FIG / "Figure_4.pdf")
    plt.close(fig)


def fig_latency(result):
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    for proto in ["ikev2", "macsec", "otn"]:
        samples = np.array([x for sr in result.service_runs
                            if sr.service.protocol == proto
                            for x in sr.latency_samples_ms])
        if len(samples):
            samples.sort()
            ax.plot(samples, np.arange(1, len(samples)+1)/len(samples),
                    lw=1.8, label=proto)
    ax.set_xlabel("sampled rekey control latency (ms)")
    ax.set_ylabel("CDF")
    ax.set_title("Protocol-specific rekey-latency distributions")
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(FIG / "Figure_5.png", dpi=FIG_DPI)
    fig.savefig(FIG / "Figure_5.pdf")
    plt.close(fig)


def fig_tco(links):
    capex = np.arange(20, 141, 10)
    pqc = []
    hybrid = []
    for c in capex:
        t = five_year_tco(links, qkd_pair_capex=float(c))
        pqc.append(t["pqc_only_npv"][-1])
        hybrid.append(t["hybrid_npv"][-1])
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.plot(capex, pqc, lw=2, label="PQC migration baseline")
    ax.plot(capex, hybrid, lw=2, marker="o", ms=3,
            label="PQC + selective QKD")
    ax.fill_between(capex, pqc, hybrid, alpha=.10,
                    label="incremental assurance premium")
    ax.set_xlabel("QKD endpoint-pair capex per physical hop (kEUR)")
    ax.set_ylabel("five-year NPV cost (kEUR)")
    ax.set_title("Illustrative cost sensitivity with physical-hop accounting")
    ax.grid(alpha=.3); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(FIG / "Figure_6.png", dpi=FIG_DPI)
    fig.savefig(FIG / "Figure_6.pdf")
    plt.close(fig)



def fig_graphical_abstract():
    """Create a legible 50 mm x 60 mm graphical TOC image at 600 dpi."""
    mm_to_in = 1.0 / 25.4
    fig, ax = plt.subplots(figsize=(50 * mm_to_in, 60 * mm_to_in))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    def box(x, y, w, h, title, subtitle="", title_size=6.0,
            subtitle_size=4.4):
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            linewidth=0.75, facecolor="white"
        )
        ax.add_patch(patch)
        ax.text(x + w/2, y + h*0.64, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", wrap=True)
        if subtitle:
            ax.text(x + w/2, y + h*0.28, subtitle, ha="center", va="center",
                    fontsize=subtitle_size, linespacing=1.05, wrap=True)

    # A vertical flow remains legible at the journal's 50 mm x 60 mm size.
    box(0.08, 0.82, 0.84, 0.12, "SERVICE CONTEXT",
        "data lifetime • capability • SLA • route")
    ax.annotate("", xy=(0.50, 0.76), xytext=(0.50, 0.82),
                arrowprops=dict(arrowstyle="->", lw=0.8))

    box(0.08, 0.62, 0.84, 0.14, "CRYPTO-AGILE POLICY",
        "risk margin • reserve forecast • downgrade rules")
    ax.annotate("", xy=(0.50, 0.56), xytext=(0.50, 0.62),
                arrowprops=dict(arrowstyle="->", lw=0.8))

    box(0.08, 0.43, 0.84, 0.13, "ADMISSIBLE PROTECTION",
        "PQ/T baseline  |  selective QKD  |  fail closed")
    ax.annotate("", xy=(0.50, 0.37), xytext=(0.50, 0.43),
                arrowprops=dict(arrowstyle="->", lw=0.8))

    box(0.08, 0.12, 0.84, 0.25, "REFERENCE SCENARIO",
        "6 of 35 links use QKD\n13 physical QKD hops\n94.15% QKD-backed preferred rekeys",
        title_size=5.8, subtitle_size=4.6)

    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
    fig.savefig(FIG / "Graphical_Abstract.png", dpi=FIG_DPI,
                bbox_inches=None, pad_inches=0)
    fig.savefig(FIG / "Graphical_Abstract.pdf", bbox_inches=None, pad_inches=0)
    plt.close(fig)

def main():
    links = build()
    inventory = phase_inventory(links)
    hndl_services = sum(r["hndl_exposed"] for r in inventory)

    mix2, d2 = phase_decisions(links, 2)
    selected = deploy_selective_qkd(links)
    mix3, d3 = phase_decisions(links, 3)
    with (RES / "decisions.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=d2[0].keys())
        w.writeheader(); w.writerows(d2+d3)

    selected_ids = [link.link_id for link in selected]
    dci = [x for x in selected_ids if x.startswith("dci")]
    core = [x for x in selected_ids if x.startswith("core")]
    metro = [x for x in selected_ids if x.startswith("metro")]
    trace_ids = tuple((dci[:1] + core[:1] + dci[1:2] + metro)[:3])
    outages = {}
    if trace_ids:
        outages[trace_ids[0]] = (9*3600, 15*3600)
    if len(trace_ids) > 1:
        outages[trace_ids[1]] = (2*3600, 5*3600)

    result = simulate(links, phase=4, outages=outages, trace_ids=trace_ids)
    tco = five_year_tco(links)

    # Negative control: an HNDL-exposed, fail-closed service with only
    # traditional capability must fail rather than silently downgrade.
    negative_links = build()
    target_link = next(x for x in negative_links if x.link_id == "dci-0")
    target_link.qkd_resources = QKDRouteResources(False, 0, 0)
    target_link.qkd_deployed = False
    target_service = next(x for x in target_link.services if x.protocol == "ikev2")
    target_service.capabilities = Capabilities(traditional=True, pqc_only=False,
                                                pqt_hybrid=False, qkd=False)
    negative = simulate(negative_links, phase=4, horizon_s=3600, seed=23)
    negative_failures = sum(sr.failed_rekeys for sr in negative.service_runs
                            if sr.service.service_id == target_service.service_id)

    total_rekeys = sum(sr.rekeys for sr in result.service_runs)
    successful = sum(sr.successful_rekeys for sr in result.service_runs)
    failures = sum(sr.failed_rekeys for sr in result.service_runs)
    deadline_misses = sum(sr.deadline_misses for sr in result.service_runs)
    proactive = sum(sr.proactive_demotions for sr in result.service_runs)
    reactive = sum(sr.reactive_fallbacks for sr in result.service_runs)
    qkd_preferred_services = {row["service"] for row in d3
                              if row["mode"] in QKD_MODES}
    qkd_preferred_runs = [sr for sr in result.service_runs
                          if sr.service.service_id in qkd_preferred_services]
    qkd_preferred_rekeys = sum(sr.rekeys for sr in qkd_preferred_runs)
    qkd_rekeys = sum(v for sr in qkd_preferred_runs
                     for m, v in sr.rekeys_by_mode.items() if m in QKD_MODES)
    non_qkd_fallback_rekeys = qkd_preferred_rekeys - qkd_rekeys
    latencies = np.array([x for sr in result.service_runs
                          for x in sr.latency_samples_ms])

    summary = {
        "links_total": len(links),
        "services_total": len(inventory),
        "hndl_exposed_services": hndl_services,
        "qkd_overlay_links": len(selected),
        "physical_qkd_hops": tco["n_physical_qkd_hops"],
        "trusted_sites": tco["n_trusted_sites"],
        "rekeys_total": total_rekeys,
        "successful_rekeys": successful,
        "failed_rekeys": failures,
        "deadline_misses": deadline_misses,
        "proactive_demotion_transition_sessions": proactive,
        "reactive_fallback_rekeys": reactive,
        "qkd_preferred_rekeys": qkd_preferred_rekeys,
        "qkd_backed_rekeys": qkd_rekeys,
        "non_qkd_fallback_rekeys": non_qkd_fallback_rekeys,
        "qkd_backed_rekey_pct": round(100*qkd_rekeys/max(qkd_preferred_rekeys,1), 3),
        "negative_control_failed_rekeys": negative_failures,
        "latency_p50_ms": round(float(np.percentile(latencies, 50)), 3),
        "latency_p99_ms": round(float(np.percentile(latencies, 99)), 3),
        "pqc_only_5y_npv_kEUR": round(float(tco["pqc_only_npv"][-1]), 1),
        "hybrid_5y_npv_kEUR": round(float(tco["hybrid_npv"][-1]), 1),
        "hybrid_premium_5y_npv_kEUR": round(float(tco["premium_npv"]), 1),
    }
    with (RES / "summary.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["metric", "value"])
        w.writerows(summary.items())

    with (RES / "service_results.csv").open("w", newline="") as f:
        fields = ["link", "service", "protocol", "rekeys", "successful",
                  "failed", "deadline_misses", "proactive_demotions",
                  "reactive_fallbacks", "modes"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for sr in result.service_runs:
            w.writerow({
                "link": sr.link.link_id,
                "service": sr.service.service_id,
                "protocol": sr.service.protocol,
                "rekeys": sr.rekeys,
                "successful": sr.successful_rekeys,
                "failed": sr.failed_rekeys,
                "deadline_misses": sr.deadline_misses,
                "proactive_demotions": sr.proactive_demotions,
                "reactive_fallbacks": sr.reactive_fallbacks,
                "modes": ";".join(f"{k}:{v}" for k,v in sorted(sr.rekeys_by_mode.items())),
            })

    fig_architecture()
    fig_qkd_routes(links)
    fig_mode_mix(mix2, mix3)
    fig_pool(result, outages, trace_ids)
    fig_latency(result)
    fig_tco(links)
    fig_graphical_abstract()

    print("[inventory]", len(links), "links,", len(inventory), "services,",
          hndl_services, "HNDL-exposed services")
    print("[phase 2]", mix2)
    print("[phase 3]", mix3, "overlay links:", selected_ids)
    print("[simulation]", summary)
    print("[done] figures and results written")


if __name__ == "__main__":
    main()
