# Reproducible crypto-agile PQC/QKD migration simulator

This archive accompanies the Original Research manuscript *A Crypto-Agile
Migration Framework for Post-Quantum Cryptography and Selective Quantum Key
Distribution in Carrier Networks*. It is a deterministic, seeded planning and
policy simulator. It does not claim carrier validation, finite-key QKD security,
wire-conformant ETSI interoperability, or production protocol integration.

## Implemented scope

- Decisions are made per service/application rather than once per link.
- Migration prioritisation uses a Mosca-style margin: confidentiality lifetime
  plus migration lead time minus planning horizon.
- Modes distinguish PQC-only, post-quantum/traditional (PQ/T) hybrid,
  QKD-assisted, and combined PQ/T+QKD operation.
- HNDL-exposed fail-closed services cannot silently downgrade to
  traditional-only operation.
- QKD route qualification requires a suitable optical path, sufficient approved
  trusted sites, and compliance with a trusted-node policy limit.
- The paired-KME domain model uses key identifiers, matching peer retrieval,
  single-use semantics, and explicit errors. It is not an ETSI GS QKD 014 REST
  server.
- IKEv2, MACsec, and OTN use separate analytical rekey adapters. RFC 9370 and
  RFC 9867 mechanisms are applied only to IKEv2; MACsec and OTN remain generic
  abstractions.
- The event-driven simulator records failures, deadline misses, proactive
  demotions, reactive fallbacks, and per-session latency samples.
- The cost model charges QKD endpoint pairs per physical hop, applies common
  orchestration costs to both strategies, discounts cash flows, and reports an
  incremental assurance premium.

## Reproduce

```bash
python3 -m pip install -r requirements.txt
python3 run_experiments.py
PYTHONPATH=. python3 -m pytest -q
```

Outputs are written to `figures/` and `results/`. Figures 1--6 are generated as
600-dpi PNG files and vector PDF files.

## Interpretation limits

Performance constants, topology, workloads, repair margins, and costs are
illustrative. Replace them with operator measurements before using the outputs
in an engineering or investment decision. Internet-Draft protocol profiles
must be cited as work in progress and version-checked on the submission date.
