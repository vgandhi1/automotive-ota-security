# Automotive OTA Security — Portfolio plan

**Meta-repo:** `vgandhi1/automotive-ota-security`  
**Consolidated:** 2026-06-28 — see [`CONSOLIDATION-CHANGELOG.md`](../CONSOLIDATION-CHANGELOG.md)

## Status (2026-06)

| Sub-project | Tier | Shipped | Open |
|-------------|------|---------|------|
| `automotive-key-provisioner/` | T1 demo | PKI hierarchy, mTLS provisioning sim, Pages deck | — |
| `OTA-firmware-verifier/` | T1 demo | Ed25519 signing, secure bootloader, anti-rollback, Pages deck | — |
| `Overdrive-OTA-Manager/` | T2 narrative | Architecture docs, presentation; partial Go/React scaffold | Full campaign orchestration (plan-docs) |

## Demo order (portfolio pitch)

1. **Key provisioner** — device identity at factory (R155)
2. **Firmware verifier** — signed image + rollback protection (R156)
3. **OTA Manager** — fleet-scale rollout (NATS + object storage)

## Governance

Inherits `governance/Guardrails/safety-baseline.md`. No project-specific guardrails file yet — add under `portfolio/GUARDRAILS.md` if scope expands.
