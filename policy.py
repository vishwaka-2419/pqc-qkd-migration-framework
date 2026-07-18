"""Explainable, service-level crypto-agility decision engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from .modes import (
    ALL_MODES, PROPERTIES, QKD_MODES, QUANTUM_RESISTANT_MODES,
    TRADITIONAL_ONLY, PQC_ONLY, PQT_HYBRID, QKD_ASSISTED,
    PQT_QKD_COMBINED,
)
from .protocols import estimate_rekey
from .qkd import QKDLinkPlan
from .topology import Link, Service


@dataclass(frozen=True)
class RuntimeState:
    phase: int
    qkd_plan: QKDLinkPlan
    qkd_deployed: bool
    qkd_reserve_time_s: float = 0.0
    qkd_reentry_ready: bool = True


@dataclass
class Decision:
    mode: str | None
    fallback_chain: list[str] = field(default_factory=list)
    rationale: str = ""
    estimated_latency_ms: float = 0.0
    candidate_scores: dict[str, float] = field(default_factory=dict)
    rejected: dict[str, str] = field(default_factory=dict)


MIN_RESERVE_S = {"gold": 2 * 3600, "silver": 3600, "bronze": 900}
REENTRY_MULTIPLIER = 1.5


def _capable(service: Service, mode: str) -> bool:
    c = service.capabilities
    return {
        TRADITIONAL_ONLY: c.traditional,
        PQC_ONLY: c.pqc_only,
        PQT_HYBRID: c.traditional and c.pqt_hybrid,
        QKD_ASSISTED: c.traditional and c.qkd,
        PQT_QKD_COMBINED: c.traditional and c.pqt_hybrid and c.qkd,
    }[mode]


def _score(service: Service, mode: str, latency_ms: float,
           qkd_plan: QKDLinkPlan) -> float:
    p = PROPERTIES[mode]
    security = p.assurance_score
    if service.hndl_exposed and mode in QUANTUM_RESISTANT_MODES:
        security += 2.0
    if service.assurance == "high" and p.qkd:
        security += 1.6
    if service.assurance == "standard" and p.qkd:
        security -= 0.8
    if mode == PQC_ONLY:
        # Target-state efficiency is useful where a protocol profile supports it,
        # but transition policy still gives PQ/T hybrid a confidence premium.
        security -= 0.25
    trusted_penalty = 0.18 * qkd_plan.n_trusted_nodes if p.qkd else 0.0
    latency_penalty = 2.0 * latency_ms / max(service.latency_budget_ms, 0.1)
    cost_penalty = p.operational_cost_score
    return security - latency_penalty - cost_penalty - trusted_penalty


def decide(link: Link, service: Service, state: RuntimeState) -> Decision:
    rejected: dict[str, str] = {}
    scores: dict[str, float] = {}
    candidates: list[str] = []
    reserve_required = MIN_RESERVE_S[service.sla_class]

    for mode in ALL_MODES:
        if state.phase >= 2 and mode == TRADITIONAL_ONLY and not service.capabilities.pqt_hybrid:
            # Legacy coexistence remains possible, but never as a silent fallback
            # for HNDL-exposed fail-closed services.
            pass
        if not _capable(service, mode):
            rejected[mode] = "endpoint capability unavailable"
            continue
        if mode in QKD_MODES:
            if state.phase < 3 or not state.qkd_deployed:
                rejected[mode] = "QKD overlay not deployed in this phase"
                continue
            if not state.qkd_plan.feasible:
                rejected[mode] = state.qkd_plan.reason
                continue
            threshold = reserve_required
            if not state.qkd_reentry_ready:
                threshold *= REENTRY_MULTIPLIER
            if state.qkd_reserve_time_s < threshold:
                rejected[mode] = "predicted QKD reserve below restoration margin"
                continue
        if service.hndl_exposed and service.fail_closed and mode == TRADITIONAL_ONLY:
            rejected[mode] = "traditional-only downgrade prohibited"
            continue
        if state.phase >= 2 and mode == TRADITIONAL_ONLY and service.capabilities.pqt_hybrid:
            rejected[mode] = "migration policy prefers quantum-resistant mode"
            continue

        cost = estimate_rekey(service.protocol, mode, link.distance_km)
        if cost.deterministic_ms > service.latency_budget_ms:
            rejected[mode] = "analytical latency exceeds budget"
            continue
        scores[mode] = _score(service, mode, cost.deterministic_ms, state.qkd_plan)
        candidates.append(mode)

    if not candidates:
        reason = (f"no admissible mode for {service.service_id}; Mosca margin "
                  f"{service.mosca_margin_yr:+d} y")
        return Decision(None, [], reason, 0.0, scores, rejected)

    ranked = sorted(candidates, key=lambda m: scores[m], reverse=True)
    selected = ranked[0]

    # Fallbacks must not weaken below the service's hard security policy.
    fallbacks = [m for m in ranked[1:]
                 if not (service.hndl_exposed and service.fail_closed
                         and m == TRADITIONAL_ONLY)]
    latency = estimate_rekey(service.protocol, selected,
                             link.distance_km).deterministic_ms
    reason = (f"selected {selected}: score {scores[selected]:.2f}; Mosca margin "
              f"{service.mosca_margin_yr:+d} y; assurance={service.assurance}; "
              f"QKD route={state.qkd_plan.reason}")
    return Decision(selected, fallbacks, reason, latency, scores, rejected)
