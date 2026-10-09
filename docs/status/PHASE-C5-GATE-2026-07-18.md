# Phase C5 Scientific Capability and Remote-Backlog Gate — 2026-07-18

> Status: `C5_LOCAL_CLASSIFIED — REMOTE_VALIDATION_PENDING`
>
> Fixed local implementation evidence: `038e7476a2b8c05ef30722eb9947363b0cbca11d`
>
> C4 release evidence remains frozen at `8ce42fe5d167bc4f41bbee596cdc9ab255591056`.

C5 closes the work that can be proven locally: it classifies every scientific backlog item, strengthens the ML/provenance seam, records the release boundary of scientific assets, and supplies a fail-closed `.53` runbook. It does **not** convert missing torch/donor-checkpoint evidence into a pass; CUDA is inventoried remotely but the current W4B path loads on CPU and is not a GPU-inference proof. The accurate next state is readiness for Phase D's read-only three-end audit, not synchronization and not remote scientific completion.

## 1. Local implementation outcome

Commit `038e747` makes the W4B path auditable without claiming a remote result:

- `ML_SLOT_CHECKPOINTS` is the single mapping shared by the builder and remote test for `MockLinear → linear_additive → LinearAdditivePredictor`, `MockCPA → latent_additive → LatentAdditivePredictor`, and `MockGEARS → gnn_pert → GNNPertPredictor`.
- Each W4B `model_version` now contains a directory-location-independent SHA-256 identity derived from the exact `.json` config and `.pt` weight bytes. The builder validates the expected sidecar class before `torch.load`.
- The identity records which checkpoint was loaded; because no independently approved digest is pinned in the repository, it is **not** a tamper-proof integrity claim.
- Gate A now rejects malformed as well as missing input/output SHA-256 strings. Existing generated per-call hashes remain lower-case 64-hex values.
- Explicit empty ML model versions fail at construction rather than silently falling back. Existing callers that omit a version retain the compatible `donor_ml:<Class>` fallback; only the W4B builder is currently content-bound.
- A no-torch adapter/runtime seam test installs three `MLBackedPredictorAgent` doubles under the real slot names. All three success paths survive Gate A; deliberately erasing one version triggers exactly `{"MockLinear": ["model_version"]}`. This proves the local adapter/governance seam, not donor tensor inference.
- The real remote test requires all three donor predictors to succeed, no rejected/failed models, exact checkpoint identities, complete per-call records, independently recomputed output hashes, and no Gate A override. Its bacteria control requires three explicit rejections and zero used models.
- Missing `W4B_CKPT_DIR` remains an honest skip/pending. After the variable is configured on a torch-capable host, missing files, wrong classes, donor/data errors, test skips, or assertion failures are not accepted as success.
- The remote bridge executes the external donor checkout and currently loads PT bundles with `weights_only=False`. Therefore directory discovery and content identity do not authorize execution: the donor Git SHA/clean state/remote and all six checkpoint digests require a separate trusted-owner approval before the runbook may import donor code or deserialize weights. Safe-format or `weights_only=True` migration remains a hardening backlog.

The per-call input hash still serializes otherwise unsupported objects with `default=str`. It must not be described as cross-device/cross-version canonical or as a cryptographic proof of the underlying tensor bytes.

## 2. Scientific backlog classification

| Item | C5 status | Evidence and boundary |
|---|---|---|
| MLBackedPredictor Gate A, local adapter/runtime seam | **met locally, narrowed** | Three accepted ML adapter doubles complete the real runtime/Gate A path; one missing version fails closed. No torch or donor inference is involved. |
| Gate A does not harm current-candidate true donor ML | **pending** | Local `--run-remote` correctly produced two skips because torch is absent. Only `2 passed / 0 skipped / 0 failed` on the approved candidate, approved donor code SHA, and separately approved W4B digest set can close this item. |
| Current `W4B_CKPT_DIR` availability | **pending** | Historical evidence at repo `390b67b` used `/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019/`; the 2026-07-17 candidate window did not relocate it. C5 made no `.53` access, so historical existence is not current availability. |
| Single-module positive success rate ≥90% | **needs_new / narrowed** | Existing real-engine cases and routing regressions prove named examples, but there is no independently labelled corpus and denominator. No percentage is reported. |
| Unsupported abstain rate ≥90% | **narrowed** | Eleven explicit Phase 10 abstain cases protect named boundaries. They are not a sampled denominator or an independently measured rate. |
| Independent result conflict detection ≥90% | **unsupported** | The implementation has a `module_plan` internal-consistency gate, not five classes of independent predictor-result conflict and not a 20-case measured corpus. |
| LLM unsupported claim count = 0 | **unsupported** | Narrative checks cover a narrow abstain/float/hedge surface, not claim-to-evidence semantics. No real-LLM corpus or independent evaluator was added. |
| Eight-module product boundary | **met only with Phase 10 qualification** | Real engine-level coverage remains four families: M2 (remote), M3, M4, M7. M1/M5/M8 are rule-based advisory; M6/EMT/fate remain limitations. The project is a governance operation layer, not a SOTA predictor. |
| Scientific asset delivery map | **classified locally** | Three MIT gene sets are packaged advisory data. Root `data/` research assets are source-only and excluded from wheel/container; private checkpoints remain manual, non-distributable/pending as recorded in the asset matrix. |

These statuses preserve the Phase 10 gate. No C5 change upgrades `narrowed`, `needs_new`, or `unsupported` scientific conclusions.

## 3. Local verification evidence

The implementation was verified from the APFS checkout in a fresh hash-locked Python `3.13.12` environment at `/tmp/praxis-c5-py313.WwA4IR`:

| Layer | Command/scope | Result |
|---|---|---|
| Dependency integrity | `python -m pip check` | PASS; no broken requirements |
| Ruff | `ruff check .` | PASS; 0 diagnostics |
| Gate A targeted + remote module under normal local marker gate | `python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py praxis_virtualcell/tests/test_ml_workflow_e2e.py -m "not llm" -o addopts='' -q -ra` | `38 passed / 2 remote skipped / 0 failed` |
| Explicit remote opt-in on this Mac | `python -m pytest praxis_virtualcell/tests/test_ml_workflow_e2e.py --run-remote -m remote -o addopts='' -q -ra` | `2 skipped / 0 failed`; both skips explicitly say no torch; this is pending, not pass |
| VirtualCell core | `python -m pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra` | `965 passed / 35 skipped / 9 deselected / 0 failed`; `17.04s` |
| Legacy CI isolation | `python -m pytest tests -m "not (integration or llm or remote)" -o addopts='' -q -ra` | `1136 passed / 59 skipped / 105 deselected / 0 failed`; `17.85s` |
| Legacy broad non-LLM | `python -m pytest tests -m "not llm" -o addopts='' -q -ra` | `1136 passed / 158 skipped / 6 deselected / 0 failed`; final compact rerun `16.17s` |
| Change hygiene | `git diff --check` on implementation and C5 docs | PASS |

The core count increased by eight local Gate A/checkpoint-identity cases from C4's frozen `957` to `965`; skip and deselection counts are unchanged. Frontend code, packaging rules, API behavior, release locks, and container code did not change in C5, so the frozen C4 frontend/wheel/container results are not re-labelled as C5 executions.

## 4. Asset and manuscript boundary

The full asset matrix is [Scientific Assets and Distribution Boundary](SCIENTIFIC-ASSETS-2026-07-18.md). The approved remote procedure is [Remote Science Validation](../runbooks/REMOTE-SCIENCE-VALIDATION.md).

The latest NMI manuscript remains a draft subordinate to `reports/phase10/PHASE10_GATE.md`. C5 did not rewrite scientific prose without an author review. Before submission, these specific gaps require a scientific-author pass:

| Draft location | Gap to correct |
|---|---|
| `manuscript.md:111-113,318` | The eight values are routing-engine enum entries, not eight validated predictors. Keep that distinction explicit; the separate M1–M8 coverage claim must retain its four-real-engine / three-advisory / M6-limitation qualification at the point where module coverage is discussed. |
| `manuscript.md:130-138` | Norman/communicative results are historical remote evidence; the current candidate's W4B Gate A E2E is still pending and must not be implied as revalidated. |
| `manuscript.md:189-225,348-354` | This draft's C1–C6/S1–S4/R1–R6 workflow table is not the Phase 10 T10.3 case set and must not be used as evidence for it. Any T10.3 claim must separately disclose that its 16 named cases contain 14 unique requests (`S3 ≡ X6`, `S8 ≡ X4`) and include governed proxy/state-characterisation evidence. |
| `manuscript.md:356-362` | “clean Linux host” overstates the present release gate; C4 proved Docker Desktop Linux/arm64 container smoke, not native Linux or amd64. |
| `manuscript.md:384-388` | Curated root-data subsets exist in the source checkout but are excluded from the release wheel/container, and third-party redistribution terms are not established by the project MIT licence. |

Until that review occurs, the manuscript is `PAPER_ALIGNMENT_PENDING`; the current product/status documentation and Phase 10 gate remain authoritative.

## 5. Gate decision and next step

`C5_LOCAL_CLASSIFIED`

- C5's local code, tests, classifications, asset ledger, and remote runbook are complete.
- Current-candidate W4B discovery and true ML Gate A execution remain `REMOTE_VALIDATION_PENDING` by design.
- No GitHub ref, `.53` repository, checkpoint, process, environment, service, tag, stash, T7 archive, or protected local asset was modified.
- This gate permits Phase D0's fresh **read-only** local/GitHub/`.53` audit and exact synchronization proposal. It does not authorize push, PR, merge, tag, checkout, fetch on `.53`, deployment, or remote test execution.
- The same approved SHA must later reach GitHub and `.53` before the remote runbook can turn the pending W4B result into candidate-specific evidence.
