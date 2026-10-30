"""Sensitivity analysis, comparison baselines, and seed-robustness study.

Everything here was added for the revised manuscript (release v1.1.0; the
matched-constraint schemes B' and F' and the corrected fallback counter in
v1.1.1). It writes CSV files to ``results/sensitivity/``; ``make_figures.py``
turns them into Figures 7-10. Run time is a few minutes on a laptop; the sweeps are
embarrassingly parallel and use a process pool.
"""
from __future__ import annotations
import csv
from multiprocessing import Pool
from pathlib import Path

from hybridsim.experiments import (run_scenario, REFERENCE_TOPOLOGY_SEED,
                                   REFERENCE_SIMULATION_SEED, NEGATIVE_CONTROL_SEED)
from hybridsim.params import PlanningParams, DEFAULT
from hybridsim.qkd import QKDRouteResources
from hybridsim.simulate import simulate
from hybridsim.tco import five_year_tco
from hybridsim.topology import build, Capabilities
from hybridsim.selection import deploy_selective_qkd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

METRIC_COLS = [
    "qkd_overlay_links", "physical_qkd_hops", "trusted_sites",
    "qkd_preferred_services", "qkd_preferred_rekeys", "qkd_backed_rekeys",
    "non_qkd_fallback_rekeys", "qkd_backed_rekey_pct",
    "proactive_demotion_transition_sessions", "reactive_fallback_rekeys",
    "mode_transitions", "kme_errors", "min_pool_fraction", "failed_rekeys",
    "deadline_misses", "downgraded_hndl_rekeys", "latency_p50_ms",
    "latency_p99_ms", "pqc_only_npv_kEUR", "hybrid_npv_kEUR", "premium_npv_kEUR",
    "hndl_exposed_services",
]

# One-at-a-time sweeps around the reference configuration.
OAT = {
    "max_hop_km": [50, 60, 70, 80, 90, 100, 120],
    "trusted_node_limit": [0, 1, 2, 3, 4, 5, 6, 8],
    "r_min_bps": [10.0, 100.0, 1e3, 1e4, 3e4, 1e5],
    "protected_fraction": [0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40],
    "reentry_multiplier": [1.0, 1.25, 1.5, 2.0, 3.0, 5.0],
    "reserve_margin_scale": [0.25, 0.5, 1.0, 1.5, 2.0, 3.0],
}

BASELINES = {
    "A_pqc_only_no_qkd": DEFAULT.with_(overlay="none"),
    "B_qkd_all_feasible_links": DEFAULT.with_(overlay="all_feasible",
                                              assume_sites_buildable=True,
                                              trusted_node_limit=8),
    "C_selective_static_threshold": DEFAULT.with_(gating="static_threshold",
                                                  static_threshold=0.20),
    "D_selective_reactive_only": DEFAULT.with_(gating="reactive_only"),
    "E_selective_no_hysteresis": DEFAULT.with_(reentry_multiplier=1.0),
    "F_proposed_selective_reserve_time": DEFAULT,
    # Matched-constraint decomposition of the B-F difference (Section 3.7 and
    # S7): scheme B changes the overlay rule AND the planning constraints
    # (every trusted site buildable, trusted-node limit 8).  B' applies the
    # selective rule under B's relaxed constraints; F' applies the
    # all-feasible rule under the reference constraints of F.
    "B_prime_selective_rule_relaxed_constraints": DEFAULT.with_(
        assume_sites_buildable=True, trusted_node_limit=8),
    "F_prime_all_feasible_rule_reference_constraints": DEFAULT.with_(
        overlay="all_feasible"),
}


def _job(args):
    tag, field, value, params, tseed, sseed = args
    out = run_scenario(params, tseed, sseed)
    row = {"sweep": tag, "parameter": field, "value": value,
           **{k: out.metrics[k] for k in METRIC_COLS}}
    return row


def _write(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def negative_control_pair() -> list[dict]:
    """Fail-closed (reference) vs fail-open variant of the negative control."""
    rows = []
    for policy in ("fail_closed", "fail_open"):
        links = build()
        deploy_selective_qkd(links)
        link = next(x for x in links if x.link_id == "dci-0")
        link.qkd_resources = QKDRouteResources(False, 0, 0)
        link.qkd_deployed = False
        svc = next(x for x in link.services if x.protocol == "ikev2")
        svc.capabilities = Capabilities(traditional=True, pqc_only=False,
                                        pqt_hybrid=False, qkd=False)
        if policy == "fail_open":
            svc.fail_closed = False
        res = simulate(links, phase=4, horizon_s=3600, seed=NEGATIVE_CONTROL_SEED)
        sr = next(x for x in res.service_runs if x.service.service_id == svc.service_id)
        rows.append({
            "policy": policy, "service": svc.service_id, "sessions": svc.sessions,
            "attempted_rekeys": sr.rekeys, "successful_rekeys": sr.successful_rekeys,
            "failed_rekeys": sr.failed_rekeys,
            "traditional_only_rekeys": sr.rekeys_by_mode.get("TRADITIONAL_ONLY", 0),
            "downgraded_hndl_rekeys": sr.downgraded_rekeys,
        })
    return rows


def cost_sensitivity() -> tuple[list[dict], list[dict]]:
    links = build()
    deploy_selective_qkd(links)
    rows = []
    for horizon in (5, 7, 10):
        for rate in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10):
            t = five_year_tco(links, horizon_years=horizon, discount_rate=rate)
            rows.append({"horizon_years": horizon, "discount_rate": rate,
                         "pqc_only_npv_kEUR": round(float(t["pqc_only_npv"][-1]), 1),
                         "hybrid_npv_kEUR": round(float(t["hybrid_npv"][-1]), 1),
                         "premium_npv_kEUR": round(float(t["premium_npv"]), 1)})
    t = five_year_tco(links)
    breakdown = [{"scope": s, "kind": k, "item": n, "npv_kEUR": round(v, 1)}
                 for s, k, n, v in t["breakdown"]]
    return rows, breakdown


def main() -> None:
    jobs = []
    for field, values in OAT.items():
        for v in values:
            jobs.append(("oat", field, v, DEFAULT.with_(**{field: v}),
                         REFERENCE_TOPOLOGY_SEED, REFERENCE_SIMULATION_SEED))
    for hop in (50, 60, 70, 80, 90, 100, 120):
        for lim in (0, 1, 2, 3, 4, 5, 6, 8):
            jobs.append(("grid", f"hop={hop}|limit={lim}", f"{hop}|{lim}",
                         DEFAULT.with_(max_hop_km=hop, trusted_node_limit=lim),
                         REFERENCE_TOPOLOGY_SEED, REFERENCE_SIMULATION_SEED))
    for name, p in BASELINES.items():
        jobs.append(("baseline", name, name, p,
                     REFERENCE_TOPOLOGY_SEED, REFERENCE_SIMULATION_SEED))
    for tseed in range(1, 21):
        jobs.append(("topology_seed", "topology_seed", tseed, DEFAULT,
                     tseed, REFERENCE_SIMULATION_SEED))
    for sseed in range(11, 31):
        jobs.append(("simulation_seed", "simulation_seed", sseed, DEFAULT,
                     REFERENCE_TOPOLOGY_SEED, sseed))

    with Pool() as pool:
        rows = pool.map(_job, jobs, chunksize=1)

    by_sweep: dict[str, list[dict]] = {}
    for r in rows:
        by_sweep.setdefault(r["sweep"], []).append(r)
    _write("oat_sweeps.csv", by_sweep.get("oat", []))
    _write("hop_limit_grid.csv", by_sweep.get("grid", []))
    _write("baselines.csv", by_sweep.get("baseline", []))
    _write("topology_seeds.csv", by_sweep.get("topology_seed", []))
    _write("simulation_seeds.csv", by_sweep.get("simulation_seed", []))
    _write("negative_control_policies.csv", negative_control_pair())
    cost_rows, breakdown = cost_sensitivity()
    _write("cost_horizon_discount.csv", cost_rows)
    _write("cost_breakdown.csv", breakdown)
    print(f"[sensitivity] {len(rows)} scenario runs written to {OUT}")


if __name__ == "__main__":
    main()
