"""Five-year planning-cost model with physical-hop QKD accounting.

Costs are illustrative parameters. The output is a cost premium and an
avoided-loss threshold, not a prediction of CRQC probability or a claim of
positive-cost breakeven.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from .qkd import plan_qkd_link
from .topology import Link


@dataclass(frozen=True)
class CostAssumptions:
    inventory_and_policy_platform: float = 280.0
    platform_opex_yr: float = 45.0
    pqc_integration_per_service: float = 4.5
    pqc_opex_per_service_yr: float = 0.8
    qkd_pair_capex_per_physical_hop: float = 100.0
    qkd_service_integration_per_link: float = 30.0
    qkd_opex_per_physical_hop_yr: float = 10.0
    trusted_site_capex: float = 80.0
    trusted_site_opex_yr: float = 8.0
    optical_engineering_per_link: float = 25.0
    migration_program_per_phase: float = 60.0
    discount_rate: float = 0.04


def selected_qkd_links(links: list[Link]) -> list[Link]:
    return [link for link in links if link.qkd_deployed
            and plan_qkd_link(link.distance_km, link.qkd_resources).feasible]


def five_year_tco(links: list[Link], assumptions: CostAssumptions | None = None,
                  qkd_pair_capex: float | None = None) -> dict:
    a = assumptions or CostAssumptions()
    if qkd_pair_capex is not None:
        a = CostAssumptions(**{**asdict(a),
                               "qkd_pair_capex_per_physical_hop": qkd_pair_capex})

    n_services = sum(len(link.services) for link in links)
    qlinks = selected_qkd_links(links)
    plans = [plan_qkd_link(link.distance_km, link.qkd_resources) for link in qlinks]
    n_physical_hops = sum(p.n_physical_hops for p in plans)
    n_trusted_sites = sum(p.n_trusted_nodes for p in plans)

    pqc_cash = np.zeros(5)
    hybrid_cash = np.zeros(5)

    common_y1 = (a.inventory_and_policy_platform
                 + n_services * a.pqc_integration_per_service
                 + 2 * a.migration_program_per_phase)
    pqc_cash[0] = common_y1
    hybrid_cash[0] = common_y1

    hybrid_cash[1] += (
        n_physical_hops * a.qkd_pair_capex_per_physical_hop
        + n_trusted_sites * a.trusted_site_capex
        + len(qlinks) * (a.qkd_service_integration_per_link
                         + a.optical_engineering_per_link)
        + a.migration_program_per_phase
    )

    for year in range(5):
        common_opex = (a.platform_opex_yr
                       + n_services * a.pqc_opex_per_service_yr)
        pqc_cash[year] += common_opex
        hybrid_cash[year] += common_opex
        if year >= 1:
            hybrid_cash[year] += (
                n_physical_hops * a.qkd_opex_per_physical_hop_yr
                + n_trusted_sites * a.trusted_site_opex_yr
            )

    discount = np.array([(1 + a.discount_rate) ** y for y in range(5)])
    pqc_npv_by_year = pqc_cash / discount
    hybrid_npv_by_year = hybrid_cash / discount
    pqc_cum = np.cumsum(pqc_npv_by_year)
    hybrid_cum = np.cumsum(hybrid_npv_by_year)
    premium = float(hybrid_cum[-1] - pqc_cum[-1])

    return {
        "pqc_only_npv": pqc_cum,
        "hybrid_npv": hybrid_cum,
        "premium_npv": premium,
        "required_avoided_loss_npv": premium,
        "n_services": n_services,
        "n_qkd_links": len(qlinks),
        "n_physical_qkd_hops": n_physical_hops,
        "n_trusted_sites": n_trusted_sites,
        "assumptions": a,
    }
