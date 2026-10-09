# Phase 16E — K562 Golden Norman perturbation→delta-expression contract completion

Work unit: P16E — exact Golden Norman K562 perturbation→delta-expression engineering contract

Outcome: ENGINEERING_COMPLETE

Overall P16 capability state: ENGINEERING_COMPLETE_SCIENCE_PENDING

Starting SHA: d1e2e37b69784bd2f440cba34f51cfb56dcc00b2

Completion code SHA: 9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2

Completion tree: 098cd563e3d865e080a0d121727b987e2d40ed18

Branch at completion: codex/p16e-k562-perturbation-contract

## Scope and protected state

P16E froze one narrow, two-scope contract family:

~~~text
NCBITaxon:9606 / Homo sapiens
+ K562 / CVCL_0004 / GRCh38 / GCA_000001405.15
+ scRNA / EFO:0008913
+ exact P8 Norman Golden source, Pack, manifests, split and control identities
+ EnsemblGene / Ensembl 84 / exact ordered 5,045-feature identity
+ CRISPR activation at dose 1.0 unit 1 and time 5d
+ one exact single-gene OR one exact two-target combination condition binding
→ 5,045 finite delta_expression values
  with condition_mean_X_minus_matched_split_control_mean_X semantics
  referenced to matched_split_control_mean_X
~~~

Single-gene and combination are separate scopes with separate perturbation, scope, protocol,
prepared input, envelope and conformance identities. The adapter passes through the exact ordered
finite vector without normalization, clipping, reordering, fill, imputation, deduplication or
absolute-expression→delta conversion. It adds strict data, perturbation, execution, negative
compatibility, scope and validation-protocol records; task-specific input/output contracts; a
prepared model input; a local-only adapter; prepared-bound output validation/projection;
deterministic synthetic conformance; and fail-closed tests.

The exact implementation diff from the starting SHA to the completion code SHA contains two paths:

- praxis_virtualcell/model_zoo/k562_golden_delta_contract.py;
- praxis_virtualcell/tests/test_k562_golden_delta_contract.py.

No checked-in Golden manifest, external asset, registry, wrapper, runtime, route, model card,
dependency declaration, version or release file was changed. `old/**`, protected repository
copies, remote refs, GitHub, `.53`, services, ports, external assets and deployment state were not
modified.

## Explicitly not performed

P16E did not:

- read, download, deserialize or execute the external Norman H5AD,
  `golden_contract.json`, NPY arrays, baseline model cache, candidate checkpoint or external
  dataset;
- import or invoke Golden benchmark/evaluation runners, GoldenBaselineWrapper, GEARS, scGPT,
  torch, anndata, h5py or another model fallback;
- train, tune or benchmark a candidate, calculate real candidate MSE, paired CI, contamination
  audit, independent K562 dataset/platform performance or OOD science results;
- rerun the P8 no-change/global-mean/additive baselines or reinterpret their historical hashes and
  score as P16 candidate evidence;
- verify arbitrary perturbation-record membership against external runtime bytes;
- create a real artifact, environment snapshot, model release, validation evidence or operator
  policy;
- update `DEFAULT_ADAPTER_REGISTRY`, registry.yaml, routing, wrappers, model cards, case dispatch
  or core runtime;
- access network, use LLM/GPU/remote compute, push, open a PR, modify main/tag, publish an artifact,
  release, deploy, operate `.53` or restart a service.

P16R remains AUTHORIZATION_REQUIRED / NOT_RUN. P16B remains NOT_RUN. Science and real model/asset
execution remain NOT_RUN.

## Contracts and immutable identities

P16E adds:

- vc.k562-golden-data-binding.v1;
- vc.k562-golden-perturbation-binding.v1;
- vc.k562-golden-execution-binding.v1;
- vc.k562-golden-compatibility-binding.v1;
- vc.k562-golden-perturbation-scope.v1;
- vc.k562-golden-validation-protocol.v1;
- vc.k562-golden-adapter-input-contract.v1;
- vc.k562-golden-adapter-output-contract.v1;
- vc.k562-golden-prepared-model-input.v1.

Adapter-global fingerprints:

- adapter: 873c4e441619da1eeeac8da3522b5c919dac0ab49b3a16cc36a74e020f55997e;
- input contract: 46dc96360506b7ec7b25609c619960e97ae613e9d05277c26fc09a21d96d1fe3;
- output contract: 10a211d99f2a2b8170e2fc9b0fb7030009849ff5e7d2968510e49c9375b21854.

Canonical shared synthetic fixture fingerprints:

- artifact: 38f21e38edcd2876095c29a342c8dc4f04c52f8afcb914079a69721211a30714;
- environment: e4764936dabfdc36bb011190a8d4b3846fa5cc73bc5d58978dffef7f4ffe0572;
- model release: a2b61b216dae1547429435b1bcc7351c7d63b4a0ec61f28338a5342bb249bb9b;
- Pack/data binding record:
  080f140a48eed4b2a8a072b262132c64cd376d5418cf1edca0a4c3ed58a7c167;
- execution binding:
  c11517270bc132ca6581019cc6449fa94e69298aae6fc0f4b9f706967c090ecb.

Canonical scope-specific fixture fingerprints:

| Identity | single_gene | combination |
|---|---|---|
| perturbation binding | 454a851530484b4993e9a1a07ccef6f724684e65b21171d32c37545c8959b6b2 | 01eb25c45e844e22a15f85b5fe4c1fc9b55c4350532450a700d86a1cc0f8f573 |
| compatibility | 5ccdeffe1cfb2188cf8dc4232aba8bc02e97be45b2bb742ec71baecd246c0f6f | 414d64b93a398080fd3172f51d76513250349f39b71ef0fe478d27f2a2f7c170 |
| scope | 14393395712f70d4e05bfa220933548695d3d619162d9a8e23f082f96b3a7f24 | 579b2eee8fd32a410443086983c224ad83ea18226c6d696332c5a8b01da0926f |
| validation protocol | 5322aa8261d786482c4d24a92e7f40bbf55fef8cecfd3819ca9bb778b274d73b | a6700ae44273cb3f788724be10239b40c89217c378c9bd2f0aedd14a6776f229 |
| prepared input | d54d10582bd5abe3a16848d1fa3fb2ad48dd16fab6b0cfb4756c4bffcb985322 | 94b541ee7a4500a33ff862d6f531ebd5a4cc6e7633c2f7db64c48057d268290a |
| output envelope | 69f948b0282a0cc1be59d8c6a5a3efa2f32848b3d4ab0bc21223e9993769b73b | add96cc86478db890a594512afe92a97c0380d79893992de01596ecef51bd1eb |
| conformance report | e3083e73df38a045e707d2117309ddf5f0fef824fc26f521f97fa4f1aba0f4c5 | 42f9612a6eb5e433a826c5b21e6a20c622df2a7dba2369c347cb01c9192ce203 |

The synthetic compatibility records are intentionally negative:
`assets_verified=false`, `executable=false`, `reason=p16r_not_authorized`. Perturbation bindings
also fix `record_membership_verified=false` with the same reason. Validation protocols are
explicitly `preregistration_not_evidence`. Synthetic artifact, environment, release, Pack/data,
perturbation and execution identities do not prove that any external candidate or asset exists or
is licensed, loadable, scientifically correct or promoted.

Frozen source SHA-256 values at the completion code commit:

- k562_golden_delta_contract.py:
  6a6f3274c8ebbef8fd3ee77865a9a5f375d2c4f5a87cc47840afbf7d08945035;
- test_k562_golden_delta_contract.py:
  4abade946f9a11934a4653b12c2f8070c4d2e04721113259023740b66c9e60e9.

## Frozen P8 source and Pack references

P16E binds the following checked-in text identities without opening referenced external assets:

| Identity | Size | SHA-256 / fingerprint |
|---|---:|---|
| contract.yaml bytes | 4,749 | 6bfc46e23e55e05a2c87dcdac9bd48da6c1f6bd2240742dc18f73ec963cf0d76 |
| pack.manifest.yaml bytes | 30,074 | 704b81da74fd96907b7e6012757b2c12104fcf3a2a3ae56af52c76d7f2c163a6 |
| artifact-manifest.json bytes | 3,864 | 724b701beda574ad344b764de09dafb86648e49c9a327df717212aaf25cc71ac |
| canonical Golden contract | — | f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5 |
| Pack | — | 42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee |
| norman_k562_golden.h5ad reference | 2,285,816,806 | 43da7aeeaca2a3ceb00ec6e9ee983b9b708b01f85922cc7afee229225a66792a |
| golden_contract.json reference | 4,663 | 456242651b50a87f507c6e9787999d4fd325beec82106363c7261cbdaa744521 |

Additional exact aggregate hashes:

- ordered feature IDs:
  ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7;
- feature records:
  1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747;
- split:
  c501e8a05514b914b216ddb2dbe0a94e709fa7a1e2214d727b831102503f956e;
- condition IDs:
  6f41dd46159a926ad476152d20c2f82e5def422f16a8213b0918af48594cabb3;
- matched control:
  2fc6ba835e3a9353345651b9369abdd189c6017a854932c038b157faa4b378ae;
- perturbation IDs:
  e69d8b83e3f69a628c545b3c44f6ad694d8406619451f1db1b6489be33fc9e21;
- condition values:
  7f3e175c495bc9499d852965869bafc23249948e0be5c87eb89e5d01befc44c9;
- perturbation records:
  0a43f9c57560f7192c0a848cb1ec044a9bf2bfdbc20d6405f98d73b3ca04d1e9;
- target IDs:
  4f58ed5c3ad7355ccba64eed0dd95e02cbcbf75a977d6aec2a1cfd5357abd64c;
- control assignment:
  8f09650026e297ce0e010120814230bc7de306364ab49316b7c102e836c6e3d5;
- unseen train target IDs:
  3bec2a15f4c5965dd32112c3508e4b70ead1724f308d597ab61e9b6210587de3.

The source `A549` value remains exactly preserved as
`upstream_metadata_error_preserved`; it is never accepted as request identity. K562 / CVCL_0004
remains canonical. The checked-in Pack text has 284 perturbation records and 286 condition IDs:
`ctrl` is record-only, while `norman.control.train`, `.validation` and `.test` are condition-only.
This intentional distinction is not repaired, filled or treated as missing data.

Canonical record proposals are:

- single-gene `AHR+ctrl` → `ENSG00000106546`, record hash
  e04567ee8d8fb3273d600b3dc8956c3f0dd35d4e4bab1d1a5ba1fb83f483b9c1;
- combination `AHR+FEV` → ordered
  `ENSG00000106546`, `ENSG00000163497`, record hash
  7b77f2c32cde91604fe8182fa38af90a991c1c10f27fdc116d6f94aa6eff2a85.

These checked-in samples do not change the typed-negative membership state.

## Frozen task, protocol and output behavior

The task/output contract is `predict_delta_expression→delta_expression` with shape `(5045,)` and
unit `None`. Requests bind K562, CVCL_0004, GRCh38/GCA_000001405.15, scRNA/EFO:0008913,
Ensembl 84 ordered features, exact CRISPR-activation dose/time, one condition/scope, split control,
P8 manifest identities and all native P12 artifact/environment/release/adapter identities.

Because core `CellContext.cell_type_id` accepts CL identifiers, exact K562 requests use
`cell_type_name=K562`, `cell_type_id=None` and bind `CVCL_0004` through strict attributes.

The P16R preregistration freezes:

- source `train→train`, `test→validation`, `ood→test` with 137/30/116 non-control conditions;
- leakage guard keyed only by condition_id;
- exact source `ctrl` plus split-specific control conditions and guide identities;
- condition-macro full-feature delta MSE, lower is better;
- condition-level additive ridge as primary comparator and historical-reference-only role;
- candidate-minus-additive paired condition bootstrap with `numpy.PCG64`, seed 0, 2,000
  replicates and interval `(0.025, 0.975)`;
- superiority only when paired-difference CI upper bound is below zero;
- same-runtime and contamination-audit requirements;
- exact stochastic seeds 11, 23 and 37;
- validation-only tuning;
- independent semantically compatible K562 dataset/platform, zero external adaptation;
- non-K562 or donor external data as OOD only;
- canonical OOD axes from iid through dose_time;
- separate single-gene and combination evaluation;
- `record_role=preregistration_not_evidence`.

Successful output is an unchanged finite 5,045-value vector with exact feature order, scope and
matched-control delta semantics. Uncertainty is `available=false`, `calibrated=false`, has no
value/sigma, and uses neutral `method=not_available` /
`reason=no_calibrated_uncertainty_declared`. `target_not_found`, `unsupported_scope` and `error`
are value-free abstentions; `unsupported_scope` also requires detected OOD. Standalone envelope
validation, projection and aggregation fail closed without the exact prepared input.

## Validation bound to completion bytes

All validation ran locally without network, external assets, H5AD/NPY/checkpoint reads, Golden
benchmark/model execution, training, LLM, GPU or remote services.

- P16E contract suite: 231 passed.
- Safe eleven-file directed gate: 689 passed.
- Safe legacy gate: 1147 passed, 58 skipped, 105 deselected.
- Authoritative `ruff check . --extend-exclude old --no-cache`: passed.
- Format check: passed.
- `git diff --check`: passed.
- Final adversarial review: no remaining P1/P2 findings.

Directed validation covered:

- test_k562_golden_delta_contract.py;
- test_yeast_deletion_fitness_contract.py;
- test_ecoli_growth_contract.py;
- test_model_adapter_sdk.py;
- test_model_adapter_output_flow.py;
- test_capability_runtime.py;
- test_model_registry_v2.py;
- test_request_v2.py;
- test_packaging.py;
- baseline/test_baseline_offline_report.py;
- baseline/test_baseline_routing_snapshot.py.

Adversarial probes included checked-in byte-size/hash drift, external path/media-type/size/hash
drift, K562/A549 identity confusion, split/control leakage, record-membership escalation,
single/combination cross-scope replay, target order/grammar drift, hidden/excluded/computed
Pydantic fields, subtype/model_copy drift, unsafe artifact load policy/media type, release
evidence/policy, feature-order/semantics/conversion drift, non-finite/unsafe values, reserved
science/policy fields, OOD/abstain contradictions and default-registry isolation.

## Packaging evidence and limitations

The exact completion code commit has build epoch:

- `SOURCE_DATE_EPOCH=1786011676`;
- wheel size: `1,108,165` bytes;
- wheel SHA-256: `d333180996a4ed91161d364275589e992d0be634582cc83a57e9758b86c03c66`;
- archive entries: `365`;
- deterministic React static entries: `14`;
- test entries: `0`;
- AppleDouble/`__MACOSX` entries: `0`;
- local toolchain: Python `3.13.12`, Node `24.14.0`, npm `11.11.1`, build `1.5.0`,
  setuptools `83.0.0`, wheel `0.47.0` and packaging `26.2`.

Two independent clean `git archive` builds for
`9f6b14ea84cb0884b2bde2ed4c67c73aeb5a37e2`, under sandbox network denial and npm offline,
produced byte-identical complete wheels with the identity above. The packaged P16E module is
present. This proves reproducibility only for the exact local source/toolchain boundary; it does
not prove dependency closure, scientific execution or publication. P15E packaging evidence was
not inherited by P16E.

The official strict `scripts/build_release_wheel.sh` path failed closed before producing a wheel:
its local hash cache did not contain locked `packaging==26.2`, and sandbox network denial prevented
index access. The global `python -m pip check` result is invalid as P16E evidence because the base
environment contains many pre-existing invalid distributions and dependency conflicts.

A Python 3.13 temporary venv with system site packages installed the wheel offline with `--no-deps`.
From outside the checkout, the installed package resolved inside that venv, the P16E adapter import
and fingerprint check passed, the default generic registry remained unchanged, and
`praxis-vc --version` returned `1.6.0`. This is a limited installed-wheel smoke only: inherited,
polluted system packages mean it is not a clean hash-locked install or dependency-integrity proof.
No artifact publication occurred.

## Engineering, science, policy and release status

Engineering:

- contract_defined=true;
- implementation_complete=true;
- tests_passed=true;
- deterministic_synthetic_conformance=true;
- default_registry_unchanged=true;
- real_assets_verified=false;
- executable=false.

Scientific evidence:

- state=NOT_RUN;
- benchmark_passed not established;
- scientifically_validated=false;
- promotion_eligible=false;
- no real candidate, baseline rerun, paired CI, contamination audit, independent K562 external or
  OOD result exists.

Product policy:

- state=NO_NEW_DECISION;
- production_promoted=false;
- no named operator decision exists.

Release:

- no product/API/runtime version bump;
- no Git tag, push, PR, artifact publication, release or deployment.

## Negative result retained and known limitations

The P9 external-validation result remains
`abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e`;
`available=false`, `scientifically_validated=false` and runtime abstention are unchanged.

Known limitations:

- no external Norman H5AD/golden contract, candidate model/checkpoint, executable environment or
  scientific result was read or produced;
- no production K562 adapter, positive model release, validation evidence or operator policy;
- the application/json data-only artifact is a synthetic identity, not a verified file;
- arbitrary perturbation-record membership is unverified;
- uncertainty is unavailable and uncalibrated;
- only exact K562/GRCh38/scRNA/Ensembl-84 CRISPR-activation delta expression is contracted;
- single-gene and combination remain separate unvalidated scopes;
- local wheel reproducibility and the limited system-site smoke do not constitute clean hash-locked
  install, dependency-integrity or release evidence;
- P16R requires exact asset paths/hashes/licenses/source/output root/run-window authorization;
- P16B requires positive P16R evidence and a named operator.

Next eligible local work unit: P17 — Virtual Cell Brain contract-only engineering. It must start
from the actual P16E docs-closure commit read from Git history, not directly from the P16E code
commit. Fewer than two P14–P16 capabilities are production-promoted, so P17 may establish the
deterministic DAG contract but cannot claim real multi-model execution. P16R and P16B remain
separate authorization windows.
