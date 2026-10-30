"""Tests added for release v1.1.0 (revised manuscript)."""
from hybridsim.experiments import run_scenario
from hybridsim.kms import PairedKMEPool
from hybridsim.params import DEFAULT
from hybridsim.qkd import QKDRouteResources, plan_qkd_link
from hybridsim.selection import deploy_selective_qkd
from hybridsim.simulate import simulate, link_qkd_demand_bps
from hybridsim.tco import five_year_tco
from hybridsim.topology import build, Capabilities


def test_defaults_reproduce_v1_0_0_headline_metrics():
    m = run_scenario().metrics
    assert m["hndl_exposed_services"] == 26
    assert m["qkd_overlay_links"] == 6
    assert m["physical_qkd_hops"] == 13
    assert m["trusted_sites"] == 7
    assert m["rekeys_total"] == 743040
    assert m["failed_rekeys"] == 0
    assert m["qkd_preferred_rekeys"] == 334080
    assert m["qkd_backed_rekeys"] == 314540
    assert abs(m["qkd_backed_rekey_pct"] - 94.151) < 1e-6
    assert abs(m["pqc_only_npv_kEUR"] - 1100.6) < 0.05
    assert abs(m["hybrid_npv_kEUR"] - 3939.2) < 0.05


def test_dimensioning_bound_matches_formula():
    pool = PairedKMEPool("x", 1000.0, "a", "b")
    demand = 341.3
    expected = (1 - 0.05) * pool.capacity_bits / demand
    assert abs(pool.max_reserve_time_s(demand, 0.05) - expected) < 1e-9
    assert pool.max_reserve_time_s(0.0) == float("inf")


def test_reserve_time_never_exceeds_dimensioning_bound():
    links = build()
    deploy_selective_qkd(links)
    for link in links:
        if not link.qkd_deployed:
            continue
        plan = plan_qkd_link(link.distance_km, link.qkd_resources)
        pool = PairedKMEPool(link.link_id, plan.skr_bps, "a", "b")
        pool.refill(1e9)  # saturate
        demand = link_qkd_demand_bps(link)
        assert pool.reserve_time_s(demand) <= pool.max_reserve_time_s(demand) + 1e-6


def test_hysteresis_above_bound_prevents_reentry():
    # kappa = 2 violates the DCI dimensioning condition (3.96 h < 4 h).
    m = run_scenario(DEFAULT.with_(reentry_multiplier=2.0)).metrics
    assert m["qkd_backed_rekey_pct"] < 85.0
    ref = run_scenario().metrics
    assert ref["qkd_backed_rekey_pct"] > 94.0


def test_route_qualification_parameters_change_footprint():
    strict = run_scenario(DEFAULT.with_(trusted_node_limit=2)).metrics
    assert strict["trusted_sites"] == 0
    assert strict["physical_qkd_hops"] == strict["qkd_overlay_links"]
    loose = run_scenario(DEFAULT.with_(trusted_node_limit=8)).metrics
    assert loose["physical_qkd_hops"] > 13


def test_reactive_only_gating_starves_pool():
    m = run_scenario(DEFAULT.with_(gating="reactive_only")).metrics
    assert m["kme_errors"] > 0
    assert m["min_pool_fraction"] == 0.0
    assert m["proactive_demotion_transition_sessions"] == 0


def test_static_threshold_gating_demotes_at_threshold():
    m = run_scenario(DEFAULT.with_(gating="static_threshold", static_threshold=0.20)).metrics
    assert m["kme_errors"] == 0
    assert m["min_pool_fraction"] < 0.21


def test_all_feasible_overlay_is_larger_and_costlier():
    p = DEFAULT.with_(overlay="all_feasible", assume_sites_buildable=True, trusted_node_limit=8)
    m = run_scenario(p).metrics
    ref = run_scenario().metrics
    assert m["qkd_overlay_links"] > ref["qkd_overlay_links"]
    assert m["physical_qkd_hops"] > ref["physical_qkd_hops"]
    assert m["premium_npv_kEUR"] > ref["premium_npv_kEUR"]


def test_no_overlay_has_zero_premium():
    m = run_scenario(DEFAULT.with_(overlay="none")).metrics
    assert m["qkd_overlay_links"] == 0
    assert m["premium_npv_kEUR"] == 0.0


def test_fail_open_control_counts_downgrades():
    links = build()
    deploy_selective_qkd(links)
    link = next(x for x in links if x.link_id == "dci-0")
    link.qkd_resources = QKDRouteResources(False, 0, 0)
    link.qkd_deployed = False
    svc = next(x for x in link.services if x.protocol == "ikev2")
    svc.capabilities = Capabilities(traditional=True, pqc_only=False, pqt_hybrid=False, qkd=False)
    svc.fail_closed = False
    res = simulate(links, phase=4, horizon_s=3600, seed=23)
    sr = next(x for x in res.service_runs if x.service.service_id == svc.service_id)
    assert sr.failed_rekeys == 0
    assert sr.downgraded_rekeys == 720


def test_tco_breakdown_sums_to_totals():
    links = build()
    deploy_selective_qkd(links)
    t = five_year_tco(links)
    shared = sum(v for s, _, _, v in t["breakdown"] if s == "shared")
    incr = sum(v for s, _, _, v in t["breakdown"] if s == "incremental")
    assert abs(shared - t["pqc_only_npv"][-1]) < 1e-6
    assert abs(incr - t["premium_npv"]) < 1e-6
    longer = five_year_tco(links, horizon_years=10)
    assert longer["premium_npv"] > t["premium_npv"]
    cheaper_money = five_year_tco(links, discount_rate=0.10)
    assert cheaper_money["premium_npv"] < t["premium_npv"]
