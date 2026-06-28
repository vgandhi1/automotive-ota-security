# Automotive OTA Security — Consolidation Changelog

**Date:** 2026-06-28  
**Phase:** Phase 2 meta-repo (Model C pillar fold)  
**Executor:** workspace consolidation pass  
**Tracking parent:** [`../REPO-CONSOLIDATION-ANALYSIS.md`](../REPO-CONSOLIDATION-ANALYSIS.md)

---

## Summary

| Metric | Before | After |
|--------|-------:|------:|
| GitHub repos (this pillar) | 3 | **1** |
| Workspace owned repos (total) | 30 | **28** |
| Local container git | none | **`vgandhi1/automotive-ota-security`** |

Three standalone repos folded into this meta-repo. **No code merged** — subfolders remain independent demos with preserved `git subtree` history.

---

## Sub-project mapping

| Archived GitHub repo | Branch imported | Subfolder (new) | Last commit SHA |
|----------------------|-----------------|-----------------|-----------------|
| `vgandhi1/OTA-firmware-verifier` | `main` | `OTA-firmware-verifier/` | `9c0831c` |
| `vgandhi1/Overdrive-OTA-Manager` | `master` | `Overdrive-OTA-Manager/` | `d5da511` |
| `vgandhi1/automotive-key-provisioner` | `main` | `automotive-key-provisioner/` | `ef429eb` |

**Local rename:** `automotive-key-provission/` (typo) → `automotive-key-provisioner/`

---

## Backups

| Artifact | Location |
|----------|----------|
| Nested `.git` dirs (pre-fold) | `/tmp/automotive-ota-gitdirs-20260628.tgz` |
| Staging build | `/tmp/ota-meta-staging/` (ephemeral) |

---

## Meta-repo additions

| Path | Purpose |
|------|---------|
| `README.md` | Pillar index + pipeline diagram |
| `.gitignore` | Cross-project artifact backstop |
| `portfolio/plan.md` | Cross-project status |
| `.github/workflows/pages.yml` | Unified gh-pages deploy (3 subpaths) |
| `CONSOLIDATION-CHANGELOG.md` | This file |

**Removed from subfolders:** per-repo `.github/workflows/pages.yml` (replaced by meta workflow)

---

## GitHub Pages URL changes

Legacy decks on **archived repos remain static** (read-only gh-pages). **Future** presentation updates deploy from this repo:

| Project | New canonical Pages URL |
|---------|-------------------------|
| Key provisioner | https://vgandhi1.github.io/automotive-ota-security/automotive-key-provisioner/ |
| Firmware verifier | https://vgandhi1.github.io/automotive-ota-security/OTA-firmware-verifier/ |
| OTA Manager | https://vgandhi1.github.io/automotive-ota-security/Overdrive-OTA-Manager/ |

---

## Inbound link updates (completed in same pass)

| File | Change |
|------|--------|
| `../vgandhi1.github.io-main/index-full.html` | Repo cards → `automotive-ota-security` + subpaths |
| `../PORTFOLIO_NOTION_PAGE.md` | Repo links → meta-repo |
| `../GIT-STATUS-AUDIT.md` | Repo count + inventory |
| `../REPO-CONSOLIDATION-ANALYSIS.md` | Phase 2 checklist tick + status |
| `../REPO-CONSOLIDATION-TRACKER.md` | Central consolidation log (new) |
| `../STANDARDS-COMPLIANCE-REPORT.md` | Pillar row → meta-repo note |

---

## Archive procedure (per retired repo)

1. ✅ Push `ARCHIVED.md` + README banner to default branch
2. ✅ `gh repo archive vgandhi1/<name> --yes`
3. ✅ Verify meta-repo pushed to `vgandhi1/automotive-ota-security`

---

## Verification checklist

- [x] Meta-repo pushed: https://github.com/vgandhi1/automotive-ota-security
- [x] Three legacy repos archived on GitHub
- [x] Portfolio + workspace tracking docs updated
- [ ] Pages workflow run + three subpath decks live
- [ ] Fresh clone smoke test

---

## Rollback (if needed)

1. Restore from `/tmp/automotive-ota-gitdirs-20260628.tgz` into separate folders
2. Unarchive GitHub repos: `gh repo unarchive` (requires admin)
3. Delete `vgandhi1/automotive-ota-security` if created
