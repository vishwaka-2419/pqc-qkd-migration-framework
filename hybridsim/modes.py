"""Mode names and assurance properties used across the simulator."""
from __future__ import annotations
from dataclasses import dataclass

TRADITIONAL_ONLY = "TRADITIONAL_ONLY"
PQC_ONLY = "PQC_ONLY"
PQT_HYBRID = "PQT_HYBRID"
QKD_ASSISTED = "QKD_ASSISTED"
PQT_QKD_COMBINED = "PQT_QKD_COMBINED"

ALL_MODES = (
    TRADITIONAL_ONLY,
    PQC_ONLY,
    PQT_HYBRID,
    QKD_ASSISTED,
    PQT_QKD_COMBINED,
)

QKD_MODES = {QKD_ASSISTED, PQT_QKD_COMBINED}
PQC_MODES = {PQC_ONLY, PQT_HYBRID, PQT_QKD_COMBINED}
QUANTUM_RESISTANT_MODES = {PQC_ONLY, PQT_HYBRID, QKD_ASSISTED, PQT_QKD_COMBINED}


@dataclass(frozen=True)
class ModeProperties:
    pqc: bool
    traditional: bool
    qkd: bool
    assurance_score: float
    operational_cost_score: float


PROPERTIES = {
    TRADITIONAL_ONLY: ModeProperties(False, True, False, 0.0, 0.1),
    PQC_ONLY: ModeProperties(True, False, False, 3.0, 0.3),
    PQT_HYBRID: ModeProperties(True, True, False, 4.0, 0.6),
    QKD_ASSISTED: ModeProperties(False, True, True, 4.0, 1.8),
    PQT_QKD_COMBINED: ModeProperties(True, True, True, 5.0, 2.2),
}
