"""Data access shared by the figure modules.

Everything is a planning-model output of the seeded synthetic scenario
(topology seed 7, simulation seed 11); no carrier data are used.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd

from hybridsim.experiments import run_scenario, ScenarioOutput
from hybridsim.params import DEFAULT
from hybridsim.policy import MIN_RESERVE_S
from hybridsim.kms import PairedKMEPool
from hybridsim.qkd import plan_qkd_link, skr_point_to_point
from hybridsim.simulate import link_qkd_demand_bps
from hybridsim.tco import five_year_tco

ROOT = Path(__file__).resolve().parents[1]
SENS = ROOT / "results" / "sensitivity"

__all__ = ["reference", "sensitivity", "DEFAULT", "MIN_RESERVE_S", "PairedKMEPool",
           "plan_qkd_link", "skr_point_to_point", "link_qkd_demand_bps",
           "five_year_tco", "ScenarioOutput", "ROOT", "SENS"]


@lru_cache(maxsize=1)
def reference() -> ScenarioOutput:
    """Reference scenario: links, selected overlay, 24-h simulation, cost."""
    return run_scenario()


def sensitivity(name: str) -> pd.DataFrame:
    """One of the CSV files written by run_sensitivity.py, e.g. 'oat_sweeps'."""
    return pd.read_csv(SENS / f"{name}.csv")
