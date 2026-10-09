# Phase 15E — S. cerevisiae deletion→fitness contract completion

Work unit: P15E — exact S. cerevisiae S288C gene-deletion→fitness engineering contract

Outcome: ENGINEERING_COMPLETE

Overall P15 capability state: ENGINEERING_COMPLETE_SCIENCE_PENDING

Starting SHA: 0ff6870a70a04d71098a16875e633f909e31cc5a

Completion code SHA: 62480a3951173a2aa7b006403af9b169521db138

Completion tree: 64906691c4c989a843df4da97f0a93f32cd65ad2

Branch at completion: codex/p15e-yeast-fitness-contract

## Scope and protected state

P15E froze one narrow contract:

~~~text
NCBITaxon:4932 / NCBITaxon:559292 / R64 / GCF_000146045.2
+ exact SGD namespace/version and target-universe mapping
+ exact condition, matched non-deletion control, assay, platform and fitness semantics
+ exactly one canonical SGD systematic complete gene deletion
→ one finite dimensionless fitness scalar
  referenced to matched_non_deletion_control_same_condition_platform
~~~

The adapter passes through the exact assay-defined scalar without ratio calculation,
normalization, clipping or a range cap. Finite negative fitness is therefore valid. It adds strict
scope, validation-protocol, data, execution, gene-mapping and negative-compatibility records;
task-specific input/output contracts; a prepared model input; a local-only adapter;
prepared-bound output validation/projection; deterministic synthetic conformance; and fail-closed
tests.

The exact implementation diff from the starting SHA to the completion code SHA contains two paths:

- praxis_virtualcell/model_zoo/yeast_deletion_fitness_contract.py;
- praxis_virtualcell/tests/test_yeast_deletion_fitness_contract.py.

No registry, wrapper, runtime, route, legacy card, dependency declaration, version or release file
was changed. old/**, the protected repository copies, remote refs, GitHub, .53, services, ports,
external assets and deployment state were not modified.

## Explicitly not performed

P15E did not:

- read, download, deserialize or execute a real deletion screen, H5AD, model artifact, checkpoint,
  GEM or scientific dataset;
- import or invoke Cobra, torch, a GEM wrapper, legacy yeast execution path or model fallback;
- train, tune or benchmark a model, calculate real MSE, paired CI, independent condition/platform
  performance or OOD science results;
- create a real Pack, artifact, environment snapshot, model release, validation evidence or
  operator policy;
- convert the P10 yeast tiny scRNA/NCBIGene fixture or planned legacy
  yeast_deletion_fitness card into a positive capability;
- update DEFAULT_ADAPTER_REGISTRY, registry.yaml, routing, wrappers, model cards, case dispatch or
  core runtime;
- access network, use LLM/GPU/remote compute, push, open a PR, modify main/tag, publish an artifact,
  release, deploy, operate .53 or restart a service.

P15R remains AUTHORIZATION_REQUIRED / NOT_RUN. P15B remains NOT_RUN. Science, real assets and GEM
execution remain NOT_RUN.

## Contracts and immutable identities

P15E adds:

- vc.yeast-deletion-fitness-scope.v1;
- vc.yeast-deletion-fitness-validation-protocol.v1;
- vc.yeast-deletion-fitness-data-binding.v1;
- vc.yeast-deletion-fitness-execution-binding.v1;
- vc.yeast-deletion-fitness-gene-mapping-binding.v1;
- vc.yeast-deletion-fitness-compatibility-binding.v1;
- vc.yeast-deletion-fitness-adapter-input-contract.v1;
- vc.yeast-deletion-fitness-adapter-output-contract.v1;
- vc.yeast-deletion-fitness-prepared-model-input.v1.

Adapter-global fingerprints:

- adapter: b1aa00416fd851b3b340bf54fcfc702bb3406e6b7007d5f80c3e46616a5e357f;
- input contract: f17599d4c40142d5b07628e1d14142d05535eab23deccb8d61f40ed040262597;
- output contract: adbf56f663b072483680fdce3bb7faa4109639b3663d35332db1e8f7ad9303ea.

Canonical synthetic fixture fingerprints:

- artifact: 5ae9b7ae69ba01c34cd7ddeb307dfbf69458fd369290e97ac286a24e1e755dcf;
- environment: 34a38273d839f1a2eddabc5ba3cbbc5e00fa8521198e403a60f8e013a019f291;
- model release: c0f476559c7d586b254e0a15126e29a684a549a2a855b64d6e5e57d85fb6e5d7;
- mapping: 71375cb49f543f9d5600b983738c87b1ef9d27489bc9f80779838ea7fb00cd83;
- execution: 5a1e7dafaa619b1a15b95029aa26b2a1ebcf4bfd8b8dcb56096f0c443cdc4e29;
- Pack/data binding record:
  f3dfbfe59d6f9277ba6d6b6255e45f4f45ab915d55d27a565535e94233535097;
- compatibility: b63327a28621ed05de6884fa4d9b701f7540570b9fed97e40346aa73c7a9f574;
- scope: b0260216a68850faad4d45469d2e649f2e0fb61ec326bf60279309af08e07e1b;
- validation protocol:
  279c5aa53f58b55d0bc62e23eaafb08ecf6263ed20a405a426eb9738928645ea;
- prepared input: 1fc11d4129c7df92d1e5f5caba9c0934161b3b747398410ebd1ec485e88dd90d;
- output envelope: 03f83e286066530e9daa38b0428f3283c8bc2f05cbd23dd2f8d70adf774812ee;
- conformance report:
  80b43f37340f3c073a0fd479ca071718fce53dc99c2a7d69cd7c39aeebed75c3.

The synthetic compatibility record is intentionally negative:
assets_verified=false, executable=false, reason=p15r_not_authorized. The validation protocol is
explicitly preregistration_not_evidence. Synthetic artifact, environment, release, Pack, mapping
and execution identities do not prove that any external file exists or is licensed, loadable,
scientifically correct or promoted.

Frozen source SHA-256 values at the completion code commit:

- yeast_deletion_fitness_contract.py:
  04377ca6200860c6bfd1d58adac9e2b76574766b1adfe65db378018deb05207c;
- test_yeast_deletion_fitness_contract.py:
  b69e395e2ee689954288ae3b8ebfe5a490e43e1916dd256124228d5596eac5d7.

## Frozen task, protocol and output behavior

The task/output contract is predict_deletion_fitness→fitness with shape (1,) and unit
dimensionless. Requests bind S288C, R64/GCF_000146045.2, one SGD systematic target, exact
condition/control/assay/platform/fitness-semantics/target-universe identities, and all
P12 model/artifact/environment/release/adapter/Pack identities.

The P15R preregistration freezes:

- held-out biological groups keyed by target_gene_id, condition_id and replicate_group_id;
- training_mean_fitness_same_condition baseline;
- mean_squared_error_fitness, lower is better;
- paired CI;
- independent condition and independent platform gates;
- zero external adaptation and validation-only tuning;
- exact stochastic seeds 11, 23 and 37;
- canonical OOD axes from strain through target;
- record_role=preregistration_not_evidence.

Successful output is an unchanged finite scalar with exact scope semantics. Uncertainty is
available=false, calibrated=false, has no value/sigma, and uses neutral
method=not_available/reason=no_calibrated_uncertainty_declared. target_not_found,
unsupported_scope and error are value-free abstentions; unsupported_scope also requires detected
OOD. Standalone envelope validation, projection and aggregation fail closed without the exact
prepared input.

## Validation bound to completion bytes

All validation ran locally without network, external assets, deletion-screen/model reads, GEM,
training, LLM, GPU or remote services.

- P15E contract suite: 98 passed.
- Safe ten-file directed gate: 458 passed.
- Safe legacy gate: 1147 passed, 58 skipped, 105 deselected.
- Authoritative ruff check . --extend-exclude old --no-cache: passed.
- Format check: passed.
- git diff --check: passed.
- Final adversarial review of exact scope, prepared/output trust boundaries, uncertainty,
  unsupported-scope OOD and local-only registry behavior: no remaining P1/P2 findings.

Directed validation covered:

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

Adversarial probes included hidden/excluded/computed Pydantic fields, model/dataclass/mapping type
drift, nested model_copy extras, unsafe artifact load policy/media type, release evidence/policy,
P10 fixture relabeling, SGD grammar, seed validation, cross-scope/provenance replay,
non-finite/unsafe values, reserved science/policy fields, OOD/abstain contradictions and
default-registry isolation.

## Packaging evidence and limitations

Two clean archives of the exact completion code commit were built independently with:

- sandbox-level network denial;
- npm offline;
- a local Python 3.13 build toolchain;
- SOURCE_DATE_EPOCH=1786006797.

The complete release-wheel bytes are identical:

- size: 1,096,472 bytes;
- SHA-256: 7758c13bd5a53c74618d556b14c6e27e0492381162a9ab3364aee7dde5d2bb8d;
- entries: 364;
- deterministic React static files: 14;
- test entries: 0;
- AppleDouble/__MACOSX entries: 0.

This proves reproducibility only for the exact local code/toolchain/sandbox build. No artifact
publication occurred.

The strict official offline script failed closed because the local cache lacked packaging==26.2
while network access was denied. The global pip check result is invalid as P15E evidence because
the pre-existing base environment is polluted. A limited Python 3.13 system-site wheel
install/import smoke succeeded; a Python 3.12 smoke failed because that environment lacked PyYAML.
Neither limited smoke is a clean isolated, hash-locked dependency installation proof. The
limitation is preserved rather than relabeled as success.

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
- no real baseline comparison, paired CI, independent condition/platform or OOD result exists.

Product policy:

- state=NO_NEW_DECISION;
- production_promoted=false;
- no named operator decision exists.

Release:

- no product/API/runtime version bump;
- no Git tag, push, PR, artifact publication, release or deployment.

## Negative result retained and known limitations

The P9 external-validation result remains
abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e;
available=false, scientifically_validated=false and runtime abstention are unchanged.

Known limitations:

- no real S. cerevisiae deletion screen, model artifact, environment execution or scientific
  result;
- no production yeast fitness adapter, model release, validation evidence or operator policy;
- the application/json data-only artifact is a synthetic identity, not a verified file;
- uncertainty is unavailable and uncalibrated;
- only one exact assay-defined scalar fitness is contracted; expression, growth, GEM flux and
  other outputs remain unsupported;
- strict official isolated offline dependency installation was not completed because the required
  packaging==26.2 cache entry was absent;
- P15R requires exact asset paths/hashes/licenses/source/output root/run-window authorization;
- P15B requires positive P15R evidence and a named operator.

Next eligible local engineering work unit: P16E — exact K562 perturbation→delta_expression
contract. It must start from the actual P15E docs-closure commit read from Git history, not directly
from the P15E code commit. P15R and P15B remain separate authorization windows.
