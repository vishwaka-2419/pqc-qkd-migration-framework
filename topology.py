"""Deterministic synthetic carrier topology with service-level contexts."""
from __future__ import annotations
from dataclasses import dataclass, field
import random
from .qkd import QKDRouteResources


@dataclass(frozen=True)
class Capabilities:
    traditional: bool = True
    pqc_only: bool = True
    pqt_hybrid: bool = True
    qkd: bool = False


@dataclass
class Service:
    service_id: str
    protocol: str
    sessions: int
    rekey_interval_s: int
    secrecy_lifetime_yr: int
    migration_lead_time_yr: int
    quantum_horizon_yr: int
    sla_class: str
    latency_budget_ms: float
    assurance: str                    # standard | high
    fail_closed: bool
    capabilities: Capabilities

    @property
    def mosca_margin_yr(self) -> int:
        return (self.secrecy_lifetime_yr + self.migration_lead_time_yr
                - self.quantum_horizon_yr)

    @property
    def hndl_exposed(self) -> bool:
        return self.mosca_margin_yr > 0


@dataclass
class Link:
    link_id: str
    kind: str
    distance_km: float
    qkd_resources: QKDRouteResources
    services: list[Service] = field(default_factory=list)
    qkd_deployed: bool = False


def _service(link_id: str, suffix: str, protocol: str, sessions: int,
             rekey_s: int, secrecy: int, migration: int, horizon: int,
             sla: str, budget: float, assurance: str, fail_closed: bool,
             caps: Capabilities) -> Service:
    return Service(f"{link_id}:{suffix}", protocol, sessions, rekey_s,
                   secrecy, migration, horizon, sla, budget, assurance,
                   fail_closed, caps)


def build(seed: int = 7) -> list[Link]:
    rng = random.Random(seed)
    links: list[Link] = []

    for i in range(6):
        link_id = f"core-{i}"
        distance = rng.uniform(240, 520)
        required_hops = max(1, int((distance + 79.999) // 80))
        required_sites = required_hops - 1
        # Deliberately mix feasible and infeasible long-haul routes.
        # Core 0/1/3 have enough approved sites; core 2 is one site short;
        # core 4 lacks a qualified optical path; core 5 exceeds policy.
        available = required_sites if i in {0, 1, 3} else max(0, required_sites - 1)
        resources = QKDRouteResources(
            dedicated_optical_path=(i != 4),
            trusted_sites_available=available,
            max_trusted_nodes_policy=4,
        )
        caps_ip = Capabilities(qkd=True)
        caps_otn = Capabilities(pqt_hybrid=False, qkd=True)
        services = [
            _service(link_id, "otn", "otn", 16, 60,
                     rng.choice([10, 15]), 5, 12, "gold", 18.0,
                     "high", True, caps_otn),
            _service(link_id, "ipsec", "ikev2", 40, 300,
                     rng.choice([5, 10, 15]), 4, 12, "gold", 22.0,
                     "high", True, caps_ip),
        ]
        links.append(Link(link_id, "core", distance, resources, services))

    for m in range(3):
        for i in range(5):
            link_id = f"metro{m}-{i}"
            distance = rng.uniform(12, 65)
            secrecy = rng.choice([2, 5, 10, 15])
            assurance = "high" if secrecy >= 10 and i % 2 == 0 else "standard"
            resources = QKDRouteResources(
                dedicated_optical_path=(assurance == "high" and i != 4),
                trusted_sites_available=0,
                max_trusted_nodes_policy=0,
            )
            caps = Capabilities(qkd=(assurance == "high"))
            services = [
                _service(link_id, "macsec", "macsec", 24, 120,
                         secrecy, 3, 12, "silver", 10.0, assurance,
                         assurance == "high", caps),
                _service(link_id, "ipsec", "ikev2", 30, 900,
                         max(2, secrecy - 3), 3, 12, "silver", 14.0,
                         "standard", False, caps),
            ]
            links.append(Link(link_id, "metro", distance, resources, services))

    for d in range(2):
        link_id = f"dci-{d}"
        distance = rng.uniform(20, 45)
        resources = QKDRouteResources(True, 0, 0)
        caps = Capabilities(qkd=True)
        caps_otn = Capabilities(pqt_hybrid=False, qkd=True)
        services = [
            _service(link_id, "otn", "otn", 8, 60, 25, 3, 12,
                     "gold", 8.0, "high", True, caps_otn),
            _service(link_id, "macsec", "macsec", 120, 120, 15, 3, 12,
                     "gold", 7.0, "high", True, caps),
            _service(link_id, "ipsec", "ikev2", 60, 300, 25, 3, 12,
                     "gold", 8.0, "high", True, caps),
        ]
        links.append(Link(link_id, "dci", distance, resources, services))

    for a in range(12):
        link_id = f"acc-{a}"
        resources = QKDRouteResources(False, 0, 0)
        legacy = a in {2, 9}
        caps = Capabilities(pqc_only=not legacy, pqt_hybrid=not legacy, qkd=False)
        services = [
            _service(link_id, "ipsec", "ikev2", 10, 3600,
                     rng.choice([1, 2, 5]), 2, 12, "bronze", 50.0,
                     "standard", False, caps),
        ]
        links.append(Link(link_id, "access", rng.uniform(2, 30),
                          resources, services))
    return links


def iter_services(links: list[Link]):
    for link in links:
        for service in link.services:
            yield link, service
