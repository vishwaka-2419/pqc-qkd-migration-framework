"""Generate the reference simulation results and tables, then Figures 1-6 and
the graphical abstract (via ``build_figures.py``; the figure code lives in
``figures_src/``).

Seeds: topology 7, event simulation 11, negative control 23. No carrier data
are used; every number is a planning-model output of the seeded synthetic
scenario. ``run_sensitivity.py`` and ``make_figures.py`` produce the
sensitivity, baseline, and robustness material (Figures 7-10).
"""
from __future__ import annotations
import csv
from pathlib import Path
from hybridsim.experiments import (run_scenario, phase_decisions,
                                   NEGATIVE_CONTROL_SEED)
from hybridsim.kms import PairedKMEPool
from hybridsim.params import DEFAULT
from hybridsim.policy import MIN_RESERVE_S, required_reserve_s
from hybridsim.qkd import plan_qkd_link, QKDRouteResources
from hybridsim.simulate import simulate, link_qkd_demand_bps
from hybridsim.topology import build, iter_services, Capabilities
from build_figures import build as build_figures

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
RES = ROOT / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------
def write_inventory(links):
    rows = []
    for link, service in iter_services(links):
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        rows.append({
            "link": link.link_id, "service": service.service_id,
            "protocol": service.protocol, "sessions": service.sessions,
            "km": round(link.distance_km, 1), "sla": service.sla_class,
            "secrecy_yr": service.secrecy_lifetime_yr,
            "migration_yr": service.migration_lead_time_yr,
            "quantum_horizon_yr": service.quantum_horizon_yr,
            "mosca_margin_yr": service.mosca_margin_yr,
            "hndl_exposed": service.hndl_exposed, "assurance": service.assurance,
            "qkd_feasible": plan.feasible, "qkd_reason": plan.reason,
            "qkd_hops": plan.n_physical_hops, "trusted_nodes": plan.n_trusted_nodes,
        })
    _csv(RES / "inventory_services.csv", rows)
    return rows


def write_dimensioning(selected):
    """Per-link check of the reserve-policy dimensioning condition.

    The binding SLA margin ``T_min`` of a link is the largest margin among its
    QKD-capable services (gold 2 h on the core and DCI links, silver 1 h on
    the metro links), so the re-entry threshold ``kappa * T_min`` and the
    largest admissible ``kappa`` are service-specific (v1.1.1; v1.1.0 applied
    the gold margin to every link).
    """
    rows = []
    for link in selected:
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        pool = PairedKMEPool(link.link_id, plan.skr_bps, "A", "B")
        demand = link_qkd_demand_bps(link)
        eligible = [s for s in link.services if s.capabilities.qkd] or list(link.services)
        sla_classes = sorted({s.sla_class for s in eligible},
                             key=lambda c: -MIN_RESERVE_S[c])
        t_min = max(required_reserve_s(s, DEFAULT) for s in eligible)
        reentry = DEFAULT.reentry_multiplier * t_min
        tmax = pool.max_reserve_time_s(demand, DEFAULT.protected_fraction)
        rows.append({
            "link": link.link_id, "km": round(link.distance_km, 1),
            "physical_hops": plan.n_physical_hops,
            "planning_skr_bps": round(plan.skr_bps, 0),
            "aggregate_demand_bps": round(demand, 1),
            "pool_capacity_Mbit": pool.capacity_bits / 1e6,
            "drain_time_from_full_h": round(pool.capacity_bits / demand / 3600, 2),
            "max_reserve_time_h": round(tmax / 3600, 2),
            "sla_classes": "/".join(sla_classes),
            "t_min_h": round(t_min / 3600, 2),
            "reentry_threshold_h": round(reentry / 3600, 2),
            "max_admissible_reentry_multiplier": round(tmax / t_min, 2),
            "condition_satisfied": tmax >= reentry,
        })
    _csv(RES / "pool_dimensioning.csv", rows)
    return rows


def _csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------
def main():
    out = run_scenario()
    links = out.links
    inventory = write_inventory(links)
    _, d2 = phase_decisions(links, 2)
    _csv(RES / "decisions.csv", d2 + out.decisions)
    write_dimensioning(out.selected)

    # Negative control: an HNDL-exposed, fail-closed service with only
    # traditional capability must fail rather than silently downgrade.
    negative_links = build()
    target_link = next(x for x in negative_links if x.link_id == "dci-0")
    target_link.qkd_resources = QKDRouteResources(False, 0, 0)
    target_link.qkd_deployed = False
    target_service = next(x for x in target_link.services if x.protocol == "ikev2")
    target_service.capabilities = Capabilities(traditional=True, pqc_only=False,
                                               pqt_hybrid=False, qkd=False)
    negative = simulate(negative_links, phase=4, horizon_s=3600, seed=NEGATIVE_CONTROL_SEED)
    negative_failures = sum(sr.failed_rekeys for sr in negative.service_runs
                            if sr.service.service_id == target_service.service_id)

    m = out.metrics
    summary = {
        "links_total": m["links_total"], "services_total": m["services_total"],
        "hndl_exposed_services": m["hndl_exposed_services"],
        "qkd_overlay_links": m["qkd_overlay_links"],
        "physical_qkd_hops": m["physical_qkd_hops"], "trusted_sites": m["trusted_sites"],
        "rekeys_total": m["rekeys_total"], "successful_rekeys": m["successful_rekeys"],
        "failed_rekeys": m["failed_rekeys"], "deadline_misses": m["deadline_misses"],
        "proactive_demotion_transition_sessions": m["proactive_demotion_transition_sessions"],
        "reactive_fallback_rekeys": m["reactive_fallback_rekeys"],
        "kme_errors": m["kme_errors"], "min_pool_fraction": m["min_pool_fraction"],
        "qkd_preferred_rekeys": m["qkd_preferred_rekeys"],
        "qkd_backed_rekeys": m["qkd_backed_rekeys"],
        "non_qkd_fallback_rekeys": m["non_qkd_fallback_rekeys"],
        "qkd_backed_rekey_pct": m["qkd_backed_rekey_pct"],
        "negative_control_failed_rekeys": negative_failures,
        "latency_p50_ms": m["latency_p50_ms"], "latency_p99_ms": m["latency_p99_ms"],
        "pqc_only_5y_npv_kEUR": m["pqc_only_npv_kEUR"],
        "hybrid_5y_npv_kEUR": m["hybrid_npv_kEUR"],
        "hybrid_premium_5y_npv_kEUR": m["premium_npv_kEUR"],
        "topology_seed": 7, "simulation_seed": 11, "negative_control_seed": NEGATIVE_CONTROL_SEED,
    }
    with (RES / "summary.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["metric", "value"]); w.writerows(summary.items())

    rows = []
    for sr in out.result.service_runs:
        rows.append({
            "link": sr.link.link_id, "service": sr.service.service_id,
            "protocol": sr.service.protocol, "rekeys": sr.rekeys,
            "successful": sr.successful_rekeys, "failed": sr.failed_rekeys,
            "deadline_misses": sr.deadline_misses,
            "proactive_demotions": sr.proactive_demotions,
            "reactive_fallbacks": sr.reactive_fallbacks,
            "mode_transitions": sr.mode_transitions,
            "modes": ";".join(f"{k}:{v}" for k, v in sorted(sr.rekeys_by_mode.items())),
        })
    _csv(RES / "service_results.csv", rows)

    build_figures(["1", "2", "3", "4", "5", "6", "GA"])

    print("[inventory]", len(links), "links,", len(inventory), "services,",
          m["hndl_exposed_services"], "HNDL-exposed services")
    print("[phase 2]", out.mix2)
    print("[phase 3]", out.mix3, "overlay links:", [l.link_id for l in out.selected])
    print("[simulation]", summary)
    print("[done] figures and results written")


if __name__ == "__main__":
    main()
