"""In-memory ETSI GS QKD 014 domain model.

This is intentionally not a wire-conformant REST implementation. It models
paired KME behavior, status fields, key identifiers, matching retrieval by a
peer SAE, single-use semantics, and explicit errors.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import uuid

KEY_SIZE_BITS = 256
DEFAULT_CAPACITY_BITS = 20_000 * KEY_SIZE_BITS


class KMEError(RuntimeError):
    pass


@dataclass(frozen=True)
class KeyMaterial:
    key_id: str
    key: bytes


@dataclass
class PairedKMEPool:
    link_id: str
    skr_bps: float
    source_kme_id: str
    target_kme_id: str
    capacity_bits: int = DEFAULT_CAPACITY_BITS
    level_bits: float = field(default=DEFAULT_CAPACITY_BITS * 0.60)
    max_keys_per_request: int = 128
    delivered: int = 0
    rejected: int = 0
    peer_mismatches: int = 0
    _outstanding: dict[str, bytes] = field(default_factory=dict)
    _counter: int = 0

    def refill(self, dt_s: float) -> None:
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        self.level_bits = min(self.capacity_bits,
                              self.level_bits + self.skr_bps * dt_s)

    def get_status(self) -> dict:
        return {
            "source_KME_ID": self.source_kme_id,
            "target_KME_ID": self.target_kme_id,
            "key_size": KEY_SIZE_BITS,
            "stored_key_count": int(self.level_bits // KEY_SIZE_BITS),
            "max_key_count": self.capacity_bits // KEY_SIZE_BITS,
            "max_key_per_request": self.max_keys_per_request,
            "min_key_size": KEY_SIZE_BITS,
            "max_key_size": KEY_SIZE_BITS,
            "key_rate_bps": self.skr_bps,
        }

    @property
    def health(self) -> float:
        return self.level_bits / self.capacity_bits

    def reserve_time_s(self, demand_bps: float, protected_fraction: float = 0.05) -> float:
        usable = max(0.0, self.level_bits - protected_fraction * self.capacity_bits)
        if demand_bps <= 0:
            return float("inf")
        return usable / demand_bps

    def _derive_key(self, key_id: str) -> bytes:
        material = f"{self.link_id}|{self._counter}|{key_id}".encode()
        return hashlib.sha256(material).digest()

    def get_enc_keys(self, number: int = 1) -> list[KeyMaterial]:
        if number < 1 or number > self.max_keys_per_request:
            self.rejected += 1
            raise KMEError("invalid number of keys requested")
        need = number * KEY_SIZE_BITS
        if self.level_bits < need:
            self.rejected += number
            raise KMEError("insufficient key material")

        result: list[KeyMaterial] = []
        for _ in range(number):
            self._counter += 1
            key_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                    f"{self.link_id}:{self._counter}"))
            key = self._derive_key(key_id)
            self._outstanding[key_id] = key
            result.append(KeyMaterial(key_id, key))
        self.level_bits -= need
        self.delivered += number
        return result

    def get_dec_keys(self, key_ids: list[str]) -> list[KeyMaterial]:
        result: list[KeyMaterial] = []
        for key_id in key_ids:
            key = self._outstanding.pop(key_id, None)
            if key is None:
                self.peer_mismatches += 1
                raise KMEError(f"unknown or already consumed key id: {key_id}")
            result.append(KeyMaterial(key_id, key))
        return result

    def deliver_matched_keys(self, number: int) -> bool:
        """Model master SAE request and peer SAE retrieval."""
        master = self.get_enc_keys(number)
        peer = self.get_dec_keys([item.key_id for item in master])
        return all(a.key_id == b.key_id and a.key == b.key
                   for a, b in zip(master, peer, strict=True))
