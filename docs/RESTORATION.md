# VirtualCell platform restoration

The legacy `NHNQNHNQ/PRAXIS-Virtualcell` repository is restored to the complete
VirtualCell platform and general agent framework source baseline
[`8bb7195`](https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/commit/8bb7195).
This is the last complete platform snapshot before the repository was adapted
toward the antibacterial project.

The restoration recovers the runtime, VirtualCellPack contracts, Model Zoo and
Adapter SDK, scientific predictors, agent orchestration, shared `praxis2`
framework, API, React/Streamlit interfaces, tests, data contracts, and historical
documents and reports. The public entry documentation is rewritten around the
[PRAXIS-VirtualCell preprint v1](https://arxiv.org/abs/2609.29221v1) and the
actual source entry points rather than the internal phase ledger.

## Repository and version scope

The change applies to the legacy VirtualCell repository. PRAXIS-Antibiotics
continues as an independent project; restoring this repository does not rewrite
that project's code or history.

The package version remains **1.7.0**, matching the restored baseline. This
restoration does not create a new tagged release, certify a release candidate,
or change repository visibility. The historical baseline and subsequent
repository development remain available through Git history. Existing
`docs/` and `reports/` preserve the detailed engineering and scientific records;
the former README ledger is also available at `8bb7195`.

## Scientific status

Source restoration does not upgrade historical evidence or model policy.
Contract conformance, software tests, successful model execution, deterministic
replay, and scientific validation retain their distinct meanings.

The checked-in K562 research release remains research-only. Historical failed
Golden gates and external stress-test limitations remain recorded. The
restoration neither promotes a model into production nor converts archived
results into new validation evidence.

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for available K562 scripts and
records, required external data and trained assets, and the incomplete packaging
of the real-data microbial benchmark pipelines.

## Public preparation fixes

The restored baseline also receives the following repository preparation fixes:

- Generated raw host audit files, `_audit/host_raw.txt` and
  `_audit/host_inventory.json`, are removed from the current tree and excluded by
  [.gitignore](../.gitignore).
- Optional HPC SSH uses explicit host, user, and key-path configuration in
  [praxis2/config.py](../praxis2/config.py), with no embedded connection defaults.
- The example PostgreSQL and Redis ports in
  [docker-compose.yml](../docker-compose.yml) bind to `127.0.0.1` for local use.
- [PROVENANCE.md](../PROVENANCE.md) retains the upstream commit and derivation
  record while removing machine-specific absolute paths.
- CI prepares hash-locked Python build and locked npm caches before the two
  offline wheel builds; the byte-comparison gate remains enabled.
- Browser tests use the platform's resolved temporary directory on macOS and
  Linux instead of a fixed macOS path.


The original host records and configuration remain in existing Git history.
These current-tree changes do not sanitize historical commits.

## Local restoration validation — 2026-10-09

Validation used an isolated CPython 3.13.14 environment installed from the
existing hash-locked build and development dependencies. External LLM, remote
compute, and integration test gates remained closed.

| Check | Result |
|---|---|
| VirtualCell core | 2,781 passed; 35 skipped; 9 deselected |
| General agent framework | 1,208 passed; 59 skipped; 105 deselected |
| Changed configuration and Compose tests | 46 passed; 1 deselected |
| Python dependency consistency and Ruff | Pass |
| React typecheck, lint, production build, bundle budget | Pass |
| Chromium end-to-end workflow | 18 passed |
| Full wheel installed outside the checkout with lean runtime dependencies | Pass |
| Installed CLI, API health, bundled static assets, offline report, unconfigured direct-v2 rejection | Pass |

Frontend validation used Node 26.4.0 and npm 11.17.0. The installed-package
verification used a real, non-symlink temporary root on macOS. These are local
software checks, not a new scientific benchmark, tagged release, or native
Linux/container certification.
