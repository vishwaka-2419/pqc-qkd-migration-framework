"""Scenario runner used by the reference experiment, the sensitivity sweeps,
the comparison baselines, and the seed-robustness study.

A *scenario* is fully described by a ``PlanningParams`` instance, a topology
seed, and a simulation seed. ``run_scenario`` returns a flat dictionary of
metrics so that every sweep writes the same CSV schema.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .modes import QKD_MODES
from .params import PlanningParams, DEFAULT
from .policy import RuntimeState, decide
from .qkd import plan_qkd_link
from .selection import deploy_selective_qkd
from .simulate import simulate, SimulationResult
from .tco import five_year_tco
from .topology import build, iter_services, Link

REFERENCE_TOPOLOGY_SEED = 7
REFERENCE_SIMULATION_SEED = 11
NEGATIVE_CONTROL_SEED = 23


def reference_outages(selected: list[Link]) -> tuple[dict, tuple[str, ...]]:
    """Reproduce the v1.0.0 outage placement from the selected overlay links."""
    ids = [link.link_id for link in selected]
    dci = [x for x in ids if x.startswith("dci")]
    core = [x for x in ids if x.startswith("core")]
    metro = [x for x in ids if x.startswith("metro")]
    trace_ids = tuple((dci[:1] + core[:1] + dci[1:2] + metro)[:3])
    outages = {}
    if trace_ids:
        outages[trace_ids[0]] = (9 * 3600, 15 * 3600)
    if len(trace_ids) > 1:
        outages[trace_ids[1]] = (2 * 3600, 5 * 3600)
    return outages, trace_ids


def phase_decisions(links: list[Link], phase: int,
                    params: PlanningParams = DEFAULT):
    rows, mix = [], {}
    for link, service in iter_services(links):
        plan = plan_qkd_link(link.distance_km, link.qkd_resources, params.r_min_bps)
        reserve = float("inf") if link.qkd_deployed and plan.feasible else 0.0
        d = decide(link, service, RuntimeState(phase, plan, link.qkd_deployed,
                                                reserve, True), params)
        key = d.mode or "NO_ADMISSIBLE_MODE"
        mix[key] = mix.get(key, 0) + 1
        rows.append({
            "phase": phase, "link": link.link_id, "service": service.service_id,
            "protocol": service.protocol, "mode": d.mode,
            "fallback_chain": ">".join(d.fallback_chain),
            "estimated_latency_ms": round(d.estimated_latency_ms, 3),
            "rationale": d.rationale,
        })
    return mix, rows


@dataclass
class ScenarioOutput:
    params: PlanningParams
    links: list[Link]
    selected: list[Link]
    outages: dict
    trace_ids: tuple[str, ...]
    result: SimulationResult
    tco: dict
    mix2: dict
    mix3: dict
    decisions: list[dict]
    metrics: dict


def summarise(result: SimulationResult, decisions3: list[dict]) -> dict:
    runs = result.service_runs
    qkd_pref = {r["service"] for r in decisions3 if r["mode"] in QKD_MODES}
    pref_runs = [sr for sr in runs if sr.service.service_id in qkd_pref]
    pref_rekeys = sum(sr.rekeys for sr in pref_runs)
    qkd_rekeys = sum(v for sr in pref_runs
                     for m, v in sr.rekeys_by_mode.items() if m in QKD_MODES)
    lat = np.array([x for sr in runs for x in sr.latency_samples_ms])
    pools = [lr for lr in result.link_runs if lr.pool]
    return {
        "rekeys_total": sum(sr.rekeys for sr in runs),
        "successful_rekeys": sum(sr.successful_rekeys for sr in runs),
        "failed_rekeys": sum(sr.failed_rekeys for sr in runs),
        "deadline_misses": sum(sr.deadline_misses for sr in runs),
        "proactive_demotion_transition_sessions": sum(sr.proactive_demotions for sr in runs),
        "reactive_fallback_rekeys": sum(sr.reactive_fallbacks for sr in runs),
        "mode_transitions": sum(sr.mode_transitions for sr in runs),
        "kme_errors": sum(lr.kme_errors for lr in pools),
        "min_pool_fraction": round(min((lr.min_pool_fraction for lr in pools), default=1.0), 4),
        "downgraded_hndl_rekeys": sum(sr.downgraded_rekeys for sr in runs),
        "qkd_preferred_rekeys": pref_rekeys,
        "qkd_backed_rekeys": qkd_rekeys,
        "non_qkd_fallback_rekeys": pref_rekeys - qkd_rekeys,
        "qkd_backed_rekey_pct": round(100 * qkd_rekeys / max(pref_rekeys, 1), 3),
        "latency_p50_ms": round(float(np.percentile(lat, 50)), 3) if len(lat) else 0.0,
        "latency_p99_ms": round(float(np.percentile(lat, 99)), 3) if len(lat) else 0.0,
    }


def run_scenario(params: PlanningParams = DEFAULT,
                 topology_seed: int = REFERENCE_TOPOLOGY_SEED,
                 simulation_seed: int = REFERENCE_SIMULATION_SEED,
                 horizon_years: int = 5,
                 discount_rate: float | None = None) -> ScenarioOutput:
    links = build(topology_seed, params)
    inventory_hndl = sum(s.hndl_exposed for _, s in iter_services(links))
    mix2, _ = phase_decisions(links, 2, params)
    selected = deploy_selective_qkd(links, params)
    mix3, d3 = phase_decisions(links, 3, params)
    outages, trace_ids = reference_outages(selected)
    result = simulate(links, phase=4, outages=outages, trace_ids=trace_ids,
                      seed=simulation_seed, params=params)
    tco = five_year_tco(links, horizon_years=horizon_years,
                        discount_rate=discount_rate, params=params)
    metrics = {
        "topology_seed": topology_seed,
        "simulation_seed": simulation_seed,
        "links_total": len(links),
        "services_total": sum(len(l.services) for l in links),
        "hndl_exposed_services": inventory_hndl,
        "qkd_overlay_links": len(selected),
        "physical_qkd_hops": tco["n_physical_qkd_hops"],
        "trusted_sites": tco["n_trusted_sites"],
        "qkd_preferred_services": sum(1 for r in d3 if r["mode"] in QKD_MODES),
        **summarise(result, d3),
        "pqc_only_npv_kEUR": round(float(tco["pqc_only_npv"][-1]), 1),
        "hybrid_npv_kEUR": round(float(tco["hybrid_npv"][-1]), 1),
        "premium_npv_kEUR": round(float(tco["premium_npv"]), 1),
    }
    return ScenarioOutput(params, links, selected, outages, trace_ids, result,
                          tco, mix2, mix3, d3, metrics)
