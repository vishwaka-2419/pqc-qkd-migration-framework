"""Regression tests for the fallback counters (release v1.1.1).

Release v1.1.0 incremented ``ServiceRun.reactive_fallbacks`` when a QKD-mode
key request failed with a KME error *and* again when the fallback mode then
carried the rekey, so one rekey could be counted twice (scheme D of the
comparison study reported 26,076 "reactive fallback rekeys" where 8,988
rekeys were carried by a fallback mode).  A rekey is now counted once, by the
mode that finally carries it; the number of unsuccessful KME requests is a
separate attempt-level counter (``LinkRun.kme_errors``).
"""
from hybridsim.experiments import run_scenario
from hybridsim.kms import PairedKMEPool, KMEError
from hybridsim.modes import QKD_MODES
from hybridsim.params import DEFAULT
from hybridsim.selection import deploy_selective_qkd
from hybridsim.simulate import simulate
from hybridsim.topology import build


def test_failed_kme_request_counts_the_rekey_once(monkeypatch):
    """Every QKD-mode key request fails: each rekey of a QKD-preferred service
    is carried by its fallback mode and counted exactly once, while the KME
    error counter records one event per unsuccessful request."""
    calls = {"n": 0}

    def always_fail(self, number):
        calls["n"] += 1
        raise KMEError("insufficient key material")

    monkeypatch.setattr(PairedKMEPool, "deliver_matched_keys", always_fail)
    links = build()
    deploy_selective_qkd(links)
    res = simulate(links, phase=4, horizon_s=3600, seed=11,
                   params=DEFAULT.with_(gating="reactive_only"))
    qkd_runs = [sr for sr in res.service_runs if sr.current_mode in QKD_MODES]
    assert qkd_runs, "the overlay links carry QKD-preferred services"
    for sr in qkd_runs:
        assert sr.reactive_fallbacks == sr.rekeys          # once per rekey, not twice
        assert sr.successful_rekeys == sr.rekeys           # the fallback mode carried it
        assert sr.failed_rekeys == 0
        assert not any(m in QKD_MODES for m in sr.rekeys_by_mode)
    other = [sr for sr in res.service_runs if sr.current_mode not in QKD_MODES]
    assert sum(sr.reactive_fallbacks for sr in other) == 0
    assert sum(lr.kme_errors for lr in res.link_runs) == calls["n"] > 0


def test_counters_are_consistent_in_the_reference_run():
    m = run_scenario().metrics
    assert m["reactive_fallback_rekeys"] <= m["non_qkd_fallback_rekeys"]
    assert m["reactive_fallback_rekeys"] + m["proactive_demotion_transition_sessions"] <= \
        m["rekeys_total"]


def test_scheme_d_reactive_fallbacks_equal_distinct_fallback_rekeys():
    """Scheme D (reactive-only gating) falls back only on failed key requests,
    so its reactive-fallback count must equal the number of QKD-preferred
    rekeys that were not QKD-backed (Table 10 and Figure 9 of the manuscript)."""
    m = run_scenario(DEFAULT.with_(gating="reactive_only")).metrics
    assert m["qkd_preferred_rekeys"] == 334080
    assert m["qkd_backed_rekeys"] == 325092
    assert m["non_qkd_fallback_rekeys"] == 8988
    assert m["reactive_fallback_rekeys"] == 8988
    assert m["kme_errors"] == 269
