"""Phase-3 QKD overlay selection, separated from runtime mode selection."""
from __future__ import annotations
from .params import PlanningParams, DEFAULT
from .qkd import plan_qkd_link
from .topology import Link


def should_overlay(link: Link, params: PlanningParams = DEFAULT) -> bool:
    plan = plan_qkd_link(link.distance_km, link.qkd_resources, params.r_min_bps)
    if not plan.feasible or params.overlay == "none":
        return False
    if params.overlay == "all_feasible":
        # Comparison baseline: classic link-level planning that equips every
        # physically qualified route, regardless of service-level demand.
        return any(service.capabilities.qkd for service in link.services)
    return any(service.hndl_exposed and service.assurance == "high"
               and service.capabilities.qkd for service in link.services)


def deploy_selective_qkd(links: list[Link],
                         params: PlanningParams = DEFAULT) -> list[Link]:
    selected: list[Link] = []
    for link in links:
        link.qkd_deployed = should_overlay(link, params)
        if link.qkd_deployed:
            selected.append(link)
    return selected
