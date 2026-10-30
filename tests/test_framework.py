from hybridsim.kms import PairedKMEPool, KMEError
from hybridsim.modes import TRADITIONAL_ONLY
from hybridsim.policy import RuntimeState, decide
from hybridsim.qkd import QKDRouteResources, plan_qkd_link
from hybridsim.selection import deploy_selective_qkd
from hybridsim.tco import five_year_tco
from hybridsim.topology import build, iter_services


def test_qkd_route_requires_resources():
    p = plan_qkd_link(240, QKDRouteResources(True, trusted_sites_available=0))
    assert not p.feasible
    assert "trusted" in p.reason


def test_paired_kme_matching_and_single_use():
    pool = PairedKMEPool("x", 1000, "a", "b")
    master = pool.get_enc_keys(2)
    peer = pool.get_dec_keys([x.key_id for x in master])
    assert [x.key for x in master] == [x.key for x in peer]
    try:
        pool.get_dec_keys([master[0].key_id])
    except KMEError:
        pass
    else:
        raise AssertionError("single-use key ID was accepted twice")


def test_no_traditional_downgrade_for_hndl_fail_closed():
    links = build()
    deploy_selective_qkd(links)
    for link, service in iter_services(links):
        if service.hndl_exposed and service.fail_closed:
            plan = plan_qkd_link(link.distance_km, link.qkd_resources)
            d = decide(link, service, RuntimeState(4, plan, link.qkd_deployed,
                                                   0.0, False))
            assert d.mode != TRADITIONAL_ONLY
            assert TRADITIONAL_ONLY not in d.fallback_chain


def test_tco_counts_physical_hops_not_logical_links():
    links = build()
    deploy_selective_qkd(links)
    t = five_year_tco(links)
    assert t["n_physical_qkd_hops"] >= t["n_qkd_links"]
    assert t["premium_npv"] > 0


def test_fail_closed_negative_control_has_failures():
    from hybridsim.qkd import QKDRouteResources
    from hybridsim.simulate import simulate
    from hybridsim.topology import Capabilities
    links = build()
    link = next(x for x in links if x.link_id == "dci-0")
    link.qkd_resources = QKDRouteResources(False, 0, 0)
    service = next(x for x in link.services if x.protocol == "ikev2")
    service.capabilities = Capabilities(traditional=True, pqc_only=False,
                                        pqt_hybrid=False, qkd=False)
    result = simulate(links, phase=4, horizon_s=600)
    sr = next(x for x in result.service_runs if x.service.service_id == service.service_id)
    assert sr.failed_rekeys > 0
