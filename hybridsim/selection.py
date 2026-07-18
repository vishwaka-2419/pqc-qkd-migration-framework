"""Phase-3 QKD overlay selection, separated from runtime mode selection."""
from __future__ import annotations
from .qkd import plan_qkd_link
from .topology import Link


def should_overlay(link: Link) -> bool:
    plan = plan_qkd_link(link.distance_km, link.qkd_resources)
    if not plan.feasible:
        return False
    return any(service.hndl_exposed and service.assurance == "high"
               and service.capabilities.qkd for service in link.services)


def deploy_selective_qkd(links: list[Link]) -> list[Link]:
    selected: list[Link] = []
    for link in links:
        link.qkd_deployed = should_overlay(link)
        if link.qkd_deployed:
            selected.append(link)
    return selected
