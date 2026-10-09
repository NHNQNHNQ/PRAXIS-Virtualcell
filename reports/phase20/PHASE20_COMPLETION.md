# Phase 20 — Virtual Cell Training Pipeline completion report

Work unit: P20 — RegisteredPack-bound, synchronous and contract-only training pipeline

Outcome: **COMPLETE — CONTRACT_ONLY**

Starting SHA: f53e29e5722a8fe48aa2eb6fe63be01f61b5cc9a

Completion code SHA: a4003704b70f06eb65297ddd32e0695ae8ee146b

Completion tree: d12d64a7c8d013d8d299272eea88a4ce0431ccab

Source date epoch: 1786040663

Branch at completion: codex/p20-training-pipeline

## Outcome and status separation

P20 adds one local engineering chain from an exact P19 factory registration to a frozen training job, pre-label
leakage audit, fixed deterministic tiny worker, safe candidate checkpoint, training result and
candidate-only model identity. It does not authorize or report real model training or scientific evidence.

| Plane | State |
|---|---|
| engineering | `COMPLETE — CONTRACT_ONLY`; exact code/tests/package evidence frozen below |
| real candidate training | NOT_RUN |
| real test/external read | NOT_RUN |
| authorized external output root | NOT_RUN; contract tests use pytest `tmp_path` only |
| GPU / remote / network | NOT_RUN |
| benchmark / science | NOT_RUN |
| product policy | NO_NEW_DECISION |
| candidate catalog | local bundle status `candidate_cataloged_contract_only`; no production write |
| production registry / promotion | unchanged / false |
| publication / release / deploy | none |

All completion identities below come from final committed code and test-controlled temporary fixtures; no
intermediate worktree identity or manual output directory is treated as completion evidence.

## Frozen contract surface

The public surface consists of:

- `TrainingEnvironmentV1` — `vc.training-environment.v1`;
- `TrainingResourceLimitsV1`, `TrainingHyperparameterV1`, `TrainingAssetBindingV1`;
- `TrainingSplitV1` — `vc.training-split.v1`;
- `LeakageOverlapV1` — `vc.training-leakage-overlap.v1`;
- `TrainingLeakageAuditV1` — `vc.training-leakage-audit.v1`;
- `TrainingJobV1` — `vc.training-job.v1`;
- `CandidateCheckpointV1` — `vc.candidate-checkpoint.v1`;
- `TrainingMetricV1`, `TrainingResourceObservationV1`, `TrainingResultV1`;
- `CandidateModelArtifactV1` and `CandidateModelCardV1`;
- `TrainingCandidateModelV1` — `vc.training-candidate-model.v1`;
- `TrainingRunBundle` serialized as `vc.training-run-bundle.v1` with nested
  `vc.training-candidate-bundle.v1`, using strict `to_dict()` serialization;
- `load_training_job(path)`, `bind_training_job(...)` and
  `run_training_job(job, *, index, output_root, cancelled=False, timeout_seconds=None)`;
- `praxis-vc training dry-run --job ... --index ... --output-root ...`.

The implementation also freezes resource ceilings, hyperparameters, asset bindings, leakage-overlap records,
training metrics/resource observations, and the strict candidate bundle schemas. Unknown fields, duplicate
JSON keys, non-finite numbers, caller-authored derived identities and inconsistent nested signatures fail closed.

## Exact P19 resolver boundary

The only valid input is a committed P19 factory registration reached through an explicit absolute Pack index.
The runner resolves `vc.pack-index.v2` registration/store provenance, opens the exact marked factory store,
replays `verify_registration()` over the full receipt/candidate/review/validation/decision chain, and matches the
index and registration bidirectionally. The stored P19 full-tree identity remains historical provenance; P20
does not claim a current recursive Pack-root rehash. Its live boundary is the exact manifest, split metadata and,
only after audit, frozen train-consumed feature/label bytes. Test/external, unconsumed and uploaded-code-looking
assets are never opened. A legacy record, raw Pack path, caller-authored registration object, missing store
commit, or drift inside the live boundary fails closed.

## Frozen job and audit-before-label boundary

The job binds exact Pack registration, feature contract and alignment report, split and leakage contract,
allowlisted train feature/label assets, trainer revision/source digest, code SHA, environment, seed,
hyperparameters, resource limits and candidate model identity. Any change must alter identity or be rejected.

The runner reads split metadata and completes the leakage audit before opening a train label. Test/external
labels are never allowlisted in P20. Pack assets that resemble code remain inert bytes; the fixed repository tiny
worker does not import or execute them. The runner verifies that worker's source, copies it to a private temporary
directory, and executes `[sys.executable, "-I", "-S", worker]` with a scrubbed environment and file-backed
stdout/stderr. Stdout is read under the checkpoint byte ceiling after successful exit and then receives strict
semantic validation; no independent stderr size cap or OS syscall sandbox is claimed. Worker count is fixed, and
no scheduler, subprocess plugin, GPU queue, distributed runtime or autotuning is introduced.

The environment records both a caller-declared dependency-lock SHA-256 and the actually observed installed-
distribution digest. The declared value is not presented as authenticated lock-file or supply-chain evidence.
The frozen code SHA identifies an explicit curated security-critical source set, not an automatically complete
Python dependency closure.

## Safe checkpoint and candidate-only boundary

The tiny checkpoint is canonical safe JSON. The runner creates a sibling staging directory under the output
parent, retains its dirfd and inode identity, writes and fsyncs the four artifacts, and reloads/re-hashes them
through that held descriptor before publishing. It revalidates the complete bundle, verifies that the named
staging source still has its creation identity, and performs an atomic no-replace rename relative to the held
parent fd. A competing destination is preserved. Failure cleanup unlinks only the four artifact basenames
through the held staging dirfd; a replacement path is untouched. The result binds the job, checkpoint, log
digest, resource summary and explicitly contract-only metrics. Artifact, card and model identities bind Pack,
checkpoint, trainer, code and environment in both directions.

Success can only produce a `candidate_cataloged_contract_only` bundle. It does not write a production model registry,
benchmark or evidence ledger and cannot set `scientifically_validated`, `promotion_eligible` or
`production_promoted`. Cancel, timeout, leakage, worker error, integrity failure or partial output cleans the
current staging area and publishes no checkpoint, result, card or candidate model; existing successful output
is neither overwritten nor deleted.

## Frozen identity ledger

| Artifact | Exact final identity |
|---|---|
| training job fingerprint | `e29d5c49059eec0346bd8f199b03602ea1ceb23fd876e90291aa9511c3affd67` |
| leakage audit fingerprint | `35ce1eaf7ea540cd05bde6045cff88dc2ea82ce7807ddda09fd60d86902b3733` |
| candidate checkpoint fingerprint | `bdc927e53447402e2b4a3050077ebaf343e752112af11d539d59acdfc70ab47d` |
| checkpoint state size / SHA-256 | `377` bytes / `950e44d437a3565320ff1ad00540f53983c785b22e11e30cbaeab72dbf24c1f9` |
| training result fingerprint | `45560256e1320494baefb724d538a6f16a7ac109b8c81e279ea2602b5dc5009c` |
| candidate model artifact fingerprint | `77be408817a9c4000a38b433409cefa37a4dd55c4822f9e2cae08d55b4f2a939` |
| candidate model card fingerprint | `2eeacc202b9f2f832bee78ffe963073d628192eb07f48dabe668e54ea2ddee58` |
| training candidate model fingerprint | `25c0bafe4d71375e00b3dce069e9b5329e954f2b213484bc411e859fd39be0fe` |
| environment fingerprint | `d37da47364978b187ebfc721c88cc912f4825950c34dd1bc7b7f7f74873b5232` |
| curated training code SHA-256 | `99481d3261a24d17e564b9a5e0a7cf30e660a5fe31e8110e518a0fcbf362f397` |
| trusted worker source SHA-256 | `4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b` |
| deterministic replay equality | passed in the focused contract suite |

All listed values must come from the final committed contract-only fixture. They are not scientific model
identities, quality scores or production registry entries.

## Frozen fail-closed coverage

Directed tests cover exact P19 resolution, identity mutation, deterministic replay,
audit-before-label ordering, leakage overlap, test/external read denial, arbitrary uploaded code inertness,
trainer/code/environment/seed/hyperparameter/resource drift, path escape, symlink, existing-output overwrite,
unsafe JSON, secret redaction, cancellation, timeout, worker failure, partial-write cleanup, checkpoint tamper and
candidate/result/card cross-binding, forged worker output and staging-source replacement.

## Validation bound to completion bytes

| Gate | Frozen result |
|---|---|
| focused P20 suite | `56 passed in 158.74s` |
| focused P19 factory/product + P20 | `99 passed, 1 skipped in 180.33s` |
| safe Python gate | `1,610 passed, 49 skipped, 387 deselected in 290.17s` |
| legacy gate | `1,147 passed, 58 skipped, 105 deselected in 62.44s` |
| Ruff lint / targeted format / py_compile / diff check | passed |
| reproducible packaging / archive integrity | passed; exact evidence below |

All successful tests must use repository fixtures and test-controlled `tmp_path`. No external output root may be
retroactively implied by a test directory, and no Golden/GEM/Norman science command belongs in these gates.
The one adjacent skip is the optional positive MuData path because `mudata` is absent locally; it was not
installed and is not reported as a pass.

## Packaging evidence and limitations

| Property | Frozen result |
|---|---|
| wheel size | `1,178,805` bytes |
| wheel SHA-256 | `2273ee71fb58fef543eae358d3df2aefccec42e80fe72a23380200718c223d79` |
| archive / React / test / AppleDouble entries | `370` / `14` / `0` / `0` |
| `pipeline.py` source/wheel SHA-256 | `dd7dbe480c3f000e5345b35fc6358fe2cc1b4377b035c31809d584ce3c869134`; exact match |
| `tiny_worker.py` source/wheel SHA-256 | `4de1ba3b67a67ea24c16b7664058939ae3a634e06cf11601a528aca4c465f02b`; exact match |
| ZIP integrity / reproducibility | passed; two wheels byte-identical |

Two independent `git archive` trees from completion SHA used `SOURCE_DATE_EPOCH=1786040663`, Node
`25.8.2` / npm `11.11.1`, and Python `3.13.12` / build `1.5.0` / setuptools `70.2.0`. Frontend install
used the existing npm cache in explicit offline mode; Python packaging used the already-installed local build
frontend with no isolation and dependency checking skipped because the exact pinned backend wheels were not
available locally. No download or network fallback was attempted. This proves reproducibility/content integrity
for the exact local source/toolchain boundary. It is not a pinned dependency-closure or clean-install proof,
release, publication, deployment, real checkpoint publication or scientific artifact.

## External, science and policy non-runs

P20 has no separately authorized exact manual CLI output root. It must not read external real data, existing
weights/checkpoints, test/external results or private services; it must not use network, GPU, remote hosts or
`.53`. It performs no real candidate training, benchmark, scientific validation, evidence creation, registry
promotion, push, release or deploy.

Tiny deterministic metrics are contract assertions only. They cannot enter an evidence ledger or be described
as predictive performance. Product policy remains `NO_NEW_DECISION`.

## Closure and next eligible work

P20 is complete only on the engineering contract plane. The next eligible work is P21A only: freeze the
benchmark system and protocol before candidate results. P21A is `SYSTEM_ONLY / NOT_COMPLETE`; P21B real candidate
run and P21C independent operator policy decision remain unauthorized and `NOT_RUN`. Neither follows from a P20
candidate model identity.

See [ADR-0017](../../docs/ADR-0017-virtual-cell-training-pipeline.md), the
[Virtual Cell Training Pipeline runbook](../../docs/runbooks/VIRTUALCELL-TRAINING-PIPELINE.md), and the
[Phase 12–30 execution plan](../../docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md).
