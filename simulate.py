"""Event-driven service rekey simulation with explicit failures and deadlines."""
from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import math
import random
from .kms import PairedKMEPool, KMEError
from .modes import QKD_MODES
from .policy import Decision, RuntimeState, decide, MIN_RESERVE_S
from .protocols import estimate_rekey
from .qkd import plan_qkd_link
from .topology import Link, Service, iter_services

KEY_BITS = 256


@dataclass
class ServiceRun:
    link: Link
    service: Service
    rekeys: int = 0
    successful_rekeys: int = 0
    failed_rekeys: int = 0
    deadline_misses: int = 0
    proactive_demotions: int = 0
    reactive_fallbacks: int = 0
    rekeys_by_mode: dict[str, int] = field(default_factory=dict)
    latency_samples_ms: list[float] = field(default_factory=list)
    decision_log: list[tuple[float, str | None, str]] = field(default_factory=list)
    current_mode: str | None = None
    qkd_blocked_by_reserve: bool = False


@dataclass
class LinkRun:
    link: Link
    pool: PairedKMEPool | None
    services: dict[str, ServiceRun]
    pool_trace: list[tuple[float, float, float]] = field(default_factory=list)
    outage_seconds: float = 0.0


@dataclass
class SimulationResult:
    link_runs: list[LinkRun]
    horizon_s: int

    @property
    def service_runs(self) -> list[ServiceRun]:
        return [s for lr in self.link_runs for s in lr.services.values()]


def link_qkd_demand_bps(link: Link) -> float:
    return sum(s.sessions * KEY_BITS / s.rekey_interval_s for s in link.services)


def _advance_pools(link_runs: list[LinkRun], previous_t: float, current_t: float,
                   outages: dict[str, tuple[int, int]]) -> None:
    if current_t <= previous_t:
        return
    for lr in link_runs:
        if not lr.pool:
            continue
        start, end = outages.get(lr.link.link_id, (-1, -1))
        # Integrate refill only over the non-outage portion of [previous_t, current_t].
        overlap = max(0.0, min(current_t, end) - max(previous_t, start))
        active = (current_t - previous_t) - overlap
        if active > 0:
            lr.pool.refill(active)
        lr.outage_seconds += overlap


def _sample_latency_ms(base_ms: float, rng: random.Random,
                       queue_scale_ms: float) -> float:
    # Positive queueing/jitter term; deterministic seed makes runs reproducible.
    jitter = rng.lognormvariate(math.log(max(queue_scale_ms, 1e-4)), 0.45)
    return base_ms + jitter


def _runtime_state(lr: LinkRun, sr: ServiceRun, phase: int) -> RuntimeState:
    plan = plan_qkd_link(lr.link.distance_km, lr.link.qkd_resources)
    demand = link_qkd_demand_bps(lr.link)
    reserve = lr.pool.reserve_time_s(demand) if lr.pool else 0.0
    required = MIN_RESERVE_S[sr.service.sla_class]
    if sr.qkd_blocked_by_reserve and reserve >= 1.5 * required:
        sr.qkd_blocked_by_reserve = False
    return RuntimeState(
        phase=phase,
        qkd_plan=plan,
        qkd_deployed=bool(lr.pool),
        qkd_reserve_time_s=reserve,
        qkd_reentry_ready=not sr.qkd_blocked_by_reserve,
    )


def simulate(links: list[Link], phase: int = 4, horizon_s: int = 86_400,
             outages: dict[str, tuple[int, int]] | None = None,
             trace_ids: tuple[str, ...] = (), seed: int = 11,
             queue_scale_ms: float = 0.08) -> SimulationResult:
    outages = outages or {}
    rng = random.Random(seed)
    link_runs: list[LinkRun] = []
    by_link: dict[str, LinkRun] = {}

    for link in links:
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        pool = None
        if link.qkd_deployed and plan.feasible:
            pool = PairedKMEPool(link.link_id, plan.skr_bps,
                                 f"{link.link_id}-KME-A", f"{link.link_id}-KME-B")
        services = {s.service_id: ServiceRun(link, s) for s in link.services}
        lr = LinkRun(link, pool, services)
        link_runs.append(lr)
        by_link[link.link_id] = lr

    events: list[tuple[float, int, str, str | None]] = []
    seq = 0
    for link, service in iter_services(links):
        seq += 1
        heapq.heappush(events, (float(service.rekey_interval_s), seq,
                                "rekey", service.service_id))
    for t in range(0, horizon_s + 1, 300):
        seq += 1
        heapq.heappush(events, (float(t), seq, "trace", None))

    last_t = 0.0
    service_index = {s.service_id: (link, s) for link, s in iter_services(links)}

    while events:
        t, _, kind, item_id = heapq.heappop(events)
        if t > horizon_s:
            break
        _advance_pools(link_runs, last_t, t, outages)
        last_t = t

        if kind == "trace":
            for lid in trace_ids:
                lr = by_link[lid]
                if lr.pool:
                    reserve_h = lr.pool.reserve_time_s(link_qkd_demand_bps(lr.link)) / 3600
                    lr.pool_trace.append((t, lr.pool.level_bits, reserve_h))
            continue

        link, service = service_index[item_id]
        lr = by_link[link.link_id]
        sr = lr.services[service.service_id]
        state = _runtime_state(lr, sr, phase)
        decision: Decision = decide(link, service, state)

        if sr.current_mode in QKD_MODES and decision.mode not in QKD_MODES:
            sr.proactive_demotions += service.sessions
            sr.qkd_blocked_by_reserve = True
        if decision.mode != sr.current_mode:
            sr.decision_log.append((t, decision.mode, decision.rationale))
            sr.current_mode = decision.mode

        sr.rekeys += service.sessions
        candidates = ([decision.mode] if decision.mode else []) + decision.fallback_chain
        selected: str | None = None

        for mode in candidates:
            if mode in QKD_MODES:
                if not lr.pool:
                    continue
                try:
                    if not lr.pool.deliver_matched_keys(service.sessions):
                        continue
                except KMEError:
                    sr.reactive_fallbacks += service.sessions
                    continue
            selected = mode
            break

        if selected is None:
            sr.failed_rekeys += service.sessions
        else:
            if selected != decision.mode:
                sr.reactive_fallbacks += service.sessions
            sr.successful_rekeys += service.sessions
            sr.rekeys_by_mode[selected] = sr.rekeys_by_mode.get(selected, 0) + service.sessions
            base = estimate_rekey(service.protocol, selected,
                                  link.distance_km).deterministic_ms
            samples = [_sample_latency_ms(base, rng, queue_scale_ms)
                       for _ in range(service.sessions)]
            sr.latency_samples_ms.extend(samples)
            sr.deadline_misses += sum(x > service.latency_budget_ms for x in samples)

        next_t = t + service.rekey_interval_s
        if next_t <= horizon_s:
            seq += 1
            heapq.heappush(events, (next_t, seq, "rekey", service.service_id))

    return SimulationResult(link_runs, horizon_s)
