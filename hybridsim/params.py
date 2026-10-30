"""Planning parameters that drive route qualification and reserve behaviour.

Every parameter here was a hard-coded constant in release v1.0.0. Collecting
them in one frozen dataclass makes the sensitivity analysis requested during
peer review explicit: a sweep constructs a modified ``PlanningParams`` and the
rest of the simulator reads from it. The defaults reproduce v1.0.0 exactly.
"""
from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PlanningParams:
    # QKD route qualification (Eq. for the attenuation envelope).
    max_hop_km: float = 80.0          # longest designed physical hop
    trusted_node_limit: int = 4       # operator policy limit on trusted nodes per route
    r_min_bps: float = 100.0          # planning floor below which a hop is unusable
    # Paired-KME reserve policy.
    protected_fraction: float = 0.05  # beta: emergency reserve never consumed by rekeys
    reentry_multiplier: float = 1.5   # hysteresis factor for QKD re-entry
    reserve_margin_scale: float = 1.0 # multiplies the gold/silver/bronze margins
    # Gating strategy used by the runtime policy (comparison baselines).
    #   "reserve_time"     predicted reserve duration vs SLA margin (proposed)
    #   "static_threshold" pool level below ``static_threshold`` fraction
    #   "reactive_only"    no proactive demotion; fall back only on KME errors
    gating: str = "reserve_time"
    static_threshold: float = 0.20
    # Phase-3 overlay selection.
    #   "selective"      HNDL-exposed, high-assurance, QKD-capable demand required
    #   "all_feasible"   every physically qualified route receives QKD
    overlay: str = "selective"
    # When True the topology assumes the operator can build every trusted site a
    # route needs (classic trusted-node network planning) instead of using the
    # approved-site inventory.
    assume_sites_buildable: bool = False

    def with_(self, **changes) -> "PlanningParams":
        return replace(self, **changes)


DEFAULT = PlanningParams()
