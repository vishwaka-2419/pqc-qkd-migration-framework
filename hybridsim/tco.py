"""Planning-cost model with physical-hop QKD accounting.

Costs are illustrative parameters. The output is a cost premium and an
avoided-loss threshold, not a prediction of CRQC probability or a claim of
positive-cost breakeven.

Release v1.1.0 adds (i) a configurable horizon and discount rate and (ii) an
itemised breakdown that separates costs shared by both strategies from the
costs that are incremental to the selective QKD overlay.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from .params import PlanningParams, DEFAULT
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


def selected_qkd_links(links: list[Link],
                       params: PlanningParams = DEFAULT) -> list[Link]:
    return [link for link in links if link.qkd_deployed
            and plan_qkd_link(link.distance_km, link.qkd_resources,
                              params.r_min_bps).feasible]


def five_year_tco(links: list[Link], assumptions: CostAssumptions | None = None,
                  qkd_pair_capex: float | None = None,
                  horizon_years: int = 5,
                  discount_rate: float | None = None,
                  params: PlanningParams = DEFAULT) -> dict:
    """Discounted planning cost over ``horizon_years`` (name kept for API stability)."""
    a = assumptions or CostAssumptions()
    overrides = {}
    if qkd_pair_capex is not None:
        overrides["qkd_pair_capex_per_physical_hop"] = qkd_pair_capex
    if discount_rate is not None:
        overrides["discount_rate"] = discount_rate
    if overrides:
        a = CostAssumptions(**{**asdict(a), **overrides})
    if horizon_years < 2:
        raise ValueError("horizon_years must be at least 2 (QKD capex lands in year 2)")

    n_services = sum(len(link.services) for link in links)
    qlinks = selected_qkd_links(links, params)
    plans = [plan_qkd_link(link.distance_km, link.qkd_resources, params.r_min_bps)
             for link in qlinks]
    n_physical_hops = sum(p.n_physical_hops for p in plans)
    n_trusted_sites = sum(p.n_trusted_nodes for p in plans)

    H = horizon_years
    pqc_cash = np.zeros(H)
    hybrid_cash = np.zeros(H)

    # ---- shared (charged to both strategies) ------------------------------
    shared_capex = {
        "Inventory and common policy platform": a.inventory_and_policy_platform,
        "PQC integration (all services)": n_services * a.pqc_integration_per_service,
        "Migration programme, phases 1-2": 2 * a.migration_program_per_phase,
    }
    shared_opex_yr = {
        "Common platform operations": a.platform_opex_yr,
        "PQC operations (all services)": n_services * a.pqc_opex_per_service_yr,
    }
    # ---- incremental (selective QKD overlay only) --------------------------
    incremental_capex = {
        "QKD endpoint pairs (per physical hop)": n_physical_hops * a.qkd_pair_capex_per_physical_hop,
        "Trusted-site construction": n_trusted_sites * a.trusted_site_capex,
        "QKD service integration (per logical link)": len(qlinks) * a.qkd_service_integration_per_link,
        "Optical engineering (per logical link)": len(qlinks) * a.optical_engineering_per_link,
        # Phase 3 is only executed when at least one route is overlaid.
        "Migration programme, phase 3": a.migration_program_per_phase if qlinks else 0.0,
    }
    incremental_opex_yr = {
        "QKD operations (per physical hop)": n_physical_hops * a.qkd_opex_per_physical_hop_yr,
        "Trusted-site operations": n_trusted_sites * a.trusted_site_opex_yr,
    }

    pqc_cash[0] = sum(shared_capex.values())
    hybrid_cash[0] = sum(shared_capex.values())
    hybrid_cash[1] += sum(incremental_capex.values())
    for year in range(H):
        pqc_cash[year] += sum(shared_opex_yr.values())
        hybrid_cash[year] += sum(shared_opex_yr.values())
        if year >= 1:
            hybrid_cash[year] += sum(incremental_opex_yr.values())

    discount = np.array([(1 + a.discount_rate) ** y for y in range(H)])
    pqc_cum = np.cumsum(pqc_cash / discount)
    hybrid_cum = np.cumsum(hybrid_cash / discount)
    premium = float(hybrid_cum[-1] - pqc_cum[-1])

    # Discounted itemised breakdown (same discounting as the cash flows).
    def _npv_capex(value, year):
        return value / discount[year]

    def _npv_opex(value_yr, first_year):
        return float(sum(value_yr / discount[y] for y in range(first_year, H)))

    breakdown = []
    for name, v in shared_capex.items():
        breakdown.append(("shared", "capex", name, _npv_capex(v, 0)))
    for name, v in shared_opex_yr.items():
        breakdown.append(("shared", "opex", name, _npv_opex(v, 0)))
    for name, v in incremental_capex.items():
        breakdown.append(("incremental", "capex", name, _npv_capex(v, 1)))
    for name, v in incremental_opex_yr.items():
        breakdown.append(("incremental", "opex", name, _npv_opex(v, 1)))

    return {
        "pqc_only_npv": pqc_cum,
        "hybrid_npv": hybrid_cum,
        "premium_npv": premium,
        "required_avoided_loss_npv": premium,
        "n_services": n_services,
        "n_qkd_links": len(qlinks),
        "n_physical_qkd_hops": n_physical_hops,
        "n_trusted_sites": n_trusted_sites,
        "horizon_years": H,
        "discount_rate": a.discount_rate,
        "breakdown": breakdown,
        "assumptions": a,
    }
