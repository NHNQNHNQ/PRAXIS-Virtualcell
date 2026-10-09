# P30A-E2b Completion Report — Archive-Only RC Runner Negative Result

**Recorded:** 2026-08-10

**Work unit:** `P30A-E2b — exact clean-source × artifact-aware source-archive runner × write-new negative record`

**Outcome:** `COMPLETE_NEGATIVE`

**Starting SHA:** `8f553389a82a9f6b5c1d08ca29885e6895f231a5`

**Completion code SHA:** `12ad93d57e4f4e7438d2110b5ac9848c6b17ea33`

**Completion tree:** `14fe604111c18c558048bc282d23da936ac57088`

**Source-date epoch:** `1786343459`

**Branch:** `codex/p30-foundation-rc`

The work unit comprises code commits `3208681080407a426f75b6f5832b0b077b592d2d`
(`artifact-aware local RC negative runner`) and
`12ad93d57e4f4e7438d2110b5ac9848c6b17ea33` (preflight-provenance hardening).

## Scope and immutable identities

P30A-E2b independently binds a controlled E2a preflight to one clean committed source identity and
uses exact-HEAD builder bytes to attempt two out-of-tree source archives. Its closed interface accepts
no caller-supplied artifact, test, result, status, evidence, release, or policy claim.

The write-new out-of-tree runner record has schema
`praxis.local-rc-artifact-aware-runner.v1` and SHA-256
`72459a3b51ba243d747ee2c0159d4105a30ba47d191b99ea05960343bbae63d2`. Its nested controlled
preflight record has SHA-256
`064a479fd35deba3b08d70e999171577b9171133873d5bc7a3d9968a57aafec4`.

The runner record observed `source_stable=true`; it records only relative artifact paths and command
output hashes, not an output-directory path, cache path, raw command output, credential, or secret.

## Changed files and contract surface

| File | SHA-256 |
|---|---|
| `scripts/run_local_rc.py` | `949517649f1d526605e0d85d65d01a0e51580fb719225a27aa30dddcbe97eda1` |
| `scripts/finalize_local_rc.py` | `003831f4370df6beb7dad5d0604d2602815d9e4791451e1cf7d46674af8ccb68` |
| `scripts/build_release_source_archive.sh` | `39d4f352cd81e0a913730a2f5b56d5a513dc43d0456f50222b8b2350a4bd9638` |
| `praxis_virtualcell/tests/test_local_rc_runner.py` | `1f72ac806f6d2e0d7f175add4e4f536db8aa20b11ede38e5e1e3d7bba4054377` |
| `praxis_virtualcell/tests/test_release_finalizer.py` | `9533193445c6ea6d43ed9e17e3b7641653cd0816bb5d72a03497eda29e6375e5` |
| `praxis_virtualcell/tests/test_release_source_archive.py` | `a6b3fbdc2d8d69b6d27e02503db8d3f465f7d02a0e113c82dfc63dd69f6c8af0` |

The only new result contract is `praxis.local-rc-artifact-aware-runner.v1`; it recursively consumes
the pre-existing negative `praxis.local-rc-finalizer-preflight.v1` record. Neither contract creates
an artifact acceptance, release, science, policy, or execution authority. Protected paths, legacy
services, existing refs, and user files were preserved.

## Exact negative result

The runner result is exactly `status=LOCAL_RC_INCOMPLETE` with
`full_gate_execution=SOURCE_ARCHIVE_ONLY_NOT_FULL_RC`,
`software_rc_gates_passed=false`, and `science_qualified_badge=false`. It records
`published=false`, `signed=false`, `tag_created=false`, `deployed=false`, and
`policy_decision_created=false`.

The nested E2a preflight remains negative for exactly two profiles:

| Target profile | Blocker |
|---|---|
| `macos_arm64_cp313` | `offline_wheel_cache_incomplete` |
| `linux_arm64_cp313` | `offline_wheel_cache_incomplete` |

Both source-archive attempts safely failed because the current committed source contains a tracked
unsupported link. The runner record retains only the stable failure reason codes and command-output
hashes; it does not turn those failed attempts into a retained artifact, a clean-install result, or a
formal RC claim.

## Validation

- Targeted P30 suite: `70 passed` (`27 + 7 + 14 + 9 + 13` across release-candidate,
  source-archive, packaging, E2a-finalizer, and E2b-runner tests).
- `ruff format --check` and `ruff check` passed for the five changed Python files; `bash -n`
  passed for the source-archive builder; `git diff --check` passed.
- The real write-new run used only existing local Git state and explicit local cache roots. Its source
  identity remained stable before and after the runner; no retained source archive was accepted.

No package installation, network access, wheel build, OCI build, full core/legacy/frontend/Ruff/
packaging gate, SBOM, licence inventory, dependency audit, `SHA256SUMS`, release manifest, push,
tag, publication, staging, deployment, rollback, real model run, benchmark, scientific evidence, or
operator decision occurred.

## Status ledger and next work

| Layer | Status |
|---|---|
| P30A-E2b archive-only runner | `COMPLETE_NEGATIVE` |
| Formal P30A local RC | `LOCAL_RC_INCOMPLETE` |
| Scientific evidence | `NOT_RUN / SCIENCE_BADGE_INELIGIBLE` |
| Product policy | `NO_NEW_DECISION` |
| P30B1/P30B2 | `NOT_AUTHORIZED / NOT_RUN` |
| P30B3/P30B4 | `NOT_AUTHORIZED / NOT_DEPLOYED` |

The next eligible local work unit is the **P16R local authorization-preflight identity bridge**. It can
prepare exact authorization and identity boundaries only; it does not access real assets, execute the
P16R candidate/comparator, create scientific evidence, or make a P16B product-policy decision. The
actual P16R scientific window remains `AUTHORIZATION_REQUIRED / NOT_RUN`.
