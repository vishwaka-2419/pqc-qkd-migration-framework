"""Protocol-specific analytical rekey models.

IKEv2 uses RFC 9370 exchange structure and RFC 9867-style PPK mixing for
CREATE_CHILD_SA. MACsec and OTN are explicitly generic adapters; no claim is
made that an IETF IKE mechanism applies to them.
"""
from __future__ import annotations
from dataclasses import dataclass
from .modes import (
    TRADITIONAL_ONLY, PQC_ONLY, PQT_HYBRID, QKD_ASSISTED,
    PQT_QKD_COMBINED,
)

FIBRE_US_PER_KM = 5.0

# Replaceable planning constants, not measured benchmarks.
CRYPTO_US = {
    TRADITIONAL_ONLY: 140.0,
    PQC_ONLY: 120.0,
    PQT_HYBRID: 250.0,
    QKD_ASSISTED: 155.0,
    PQT_QKD_COMBINED: 265.0,
}
WIRE_BYTES = {
    TRADITIONAL_ONLY: 96,
    PQC_ONLY: 2300,
    PQT_HYBRID: 2400,
    QKD_ASSISTED: 160,
    PQT_QKD_COMBINED: 2460,
}


@dataclass(frozen=True)
class RekeyCost:
    protocol: str
    mode: str
    control_round_trips: float
    deterministic_ms: float
    bytes_on_wire: int
    standards_note: str


def rtt_ms(distance_km: float) -> float:
    return 2.0 * distance_km * FIBRE_US_PER_KM / 1000.0


def estimate_rekey(protocol: str, mode: str, distance_km: float,
                   kme_access_ms: float = 0.40) -> RekeyCost:
    """Return a protocol-specific deterministic rekey cost."""
    rtt = rtt_ms(distance_km)
    qkd = mode in {QKD_ASSISTED, PQT_QKD_COMBINED}
    pqc = mode in {PQC_ONLY, PQT_HYBRID, PQT_QKD_COMBINED}

    if protocol == "ikev2":
        # CREATE_CHILD_SA is one RTT. RFC 9370 adds IKE_FOLLOWUP_KE for an
        # additional exchange. RFC 9867 PPK mixing adds no IKE RTT, but an
        # external KME lookup is modeled separately.
        rounds = 1.0 + (1.0 if mode in {PQT_HYBRID, PQT_QKD_COMBINED} else 0.0)
        fixed_ms = CRYPTO_US[mode] / 1000.0 + (kme_access_ms if qkd else 0.0)
        note = "RFC 9370 / RFC 9867 analytical CREATE_CHILD_SA model"
    elif protocol == "macsec":
        # Generic MKA/key-server control and installation abstraction.
        rounds = 1.0
        fixed_ms = 0.55 + CRYPTO_US[mode] / 1000.0 + (kme_access_ms if qkd else 0.0)
        note = "generic MACsec/MKA adapter; not an IETF PQC binding"
    elif protocol == "otn":
        # Controller-to-encryptor distribution plus hardware activation.
        rounds = 0.5
        fixed_ms = 1.60 + CRYPTO_US[mode] / 1000.0 + (kme_access_ms if qkd else 0.0)
        note = "generic OTN encryptor adapter; vendor profile required"
    else:
        raise ValueError(f"unsupported protocol: {protocol}")

    return RekeyCost(protocol, mode, rounds, rounds * rtt + fixed_ms,
                     WIRE_BYTES[mode], note)
