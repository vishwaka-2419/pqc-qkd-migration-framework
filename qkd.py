"""QKD route-planning abstraction.

The model is deliberately an attenuation-envelope planner, not a finite-key
security proof. Unlike the original prototype, long routes are not made
feasible automatically: feasibility requires an optical path and enough
operator-approved trusted sites.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

ALPHA_DB_PER_KM = 0.20
SYSTEM_LOSS_DB = 3.0
R0_BPS = 2.0e6
MIN_USABLE_SKR_BPS = 100.0
MAX_DESIGN_HOP_KM = 80.0


def skr_point_to_point(distance_km: float) -> float:
    """Return the planning-envelope SKR for one fibre span."""
    if distance_km < 0:
        raise ValueError("distance_km must be non-negative")
    loss_db = ALPHA_DB_PER_KM * distance_km + SYSTEM_LOSS_DB
    rate = R0_BPS * 10 ** (-loss_db / 10)
    return rate if rate >= MIN_USABLE_SKR_BPS else 0.0


@dataclass(frozen=True)
class QKDRouteResources:
    dedicated_optical_path: bool
    trusted_sites_available: int = 0
    max_trusted_nodes_policy: int = 4
    max_hop_km: float = MAX_DESIGN_HOP_KM


@dataclass(frozen=True)
class QKDLinkPlan:
    distance_km: float
    n_physical_hops: int
    n_trusted_nodes: int
    hop_km: float
    skr_bps: float
    feasible: bool
    reason: str


def plan_qkd_link(distance_km: float, resources: QKDRouteResources) -> QKDLinkPlan:
    """Plan a direct or trusted-node QKD service under explicit constraints."""
    if distance_km <= 0:
        return QKDLinkPlan(distance_km, 0, 0, 0.0, 0.0, False,
                           "invalid route distance")
    if not resources.dedicated_optical_path:
        return QKDLinkPlan(distance_km, 0, 0, 0.0, 0.0, False,
                           "no qualified optical path")

    hops = max(1, math.ceil(distance_km / resources.max_hop_km))
    trusted = hops - 1
    hop_km = distance_km / hops

    if trusted > resources.max_trusted_nodes_policy:
        return QKDLinkPlan(distance_km, hops, trusted, hop_km, 0.0, False,
                           "trusted-node policy limit exceeded")
    if trusted > resources.trusted_sites_available:
        return QKDLinkPlan(distance_km, hops, trusted, hop_km, 0.0, False,
                           "insufficient approved trusted sites")

    rate = skr_point_to_point(hop_km)
    if rate <= 0:
        return QKDLinkPlan(distance_km, hops, trusted, hop_km, 0.0, False,
                           "per-hop SKR below planning floor")
    return QKDLinkPlan(distance_km, hops, trusted, hop_km, rate, True,
                       "qualified route")
