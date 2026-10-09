# Phase 14E — E. coli K-12 knockout→growth contract completion

Work unit: P14E — exact E. coli K-12 MG1655 knockout→growth-ratio engineering contract

Outcome: ENGINEERING_COMPLETE

Overall P14 capability state: ENGINEERING_COMPLETE_SCIENCE_PENDING

Starting SHA: 0b193310009d6e4d2ebc0fc8abf95da20a56acdb

SDK trust-boundary prerequisite SHA: c3401450fd79f7829c438d6b55c1902ea2f4cf5f

Completion code SHA: 8778e93c31c2dfe1ef0f77f06e7a80a425633736

Completion tree: fa85e049bb36f3fbd8e6d4a7503e4b5837ed7c78

Branch at completion: codex/p14e-ecoli-growth-contract

## Scope and protected state

P14E froze one narrow contract:

~~~text
NCBITaxon:562 / NCBITaxon:511145 / GCF_000005845.2
+ exact GEM, medium, condition, objective, solver and NCBIGene mapping identities
+ exactly one canonical NCBIGene knockout
→ one dimensionless growth_ratio
  referenced to wild_type_same_gem_medium_condition
~~~

It added strict scope, protocol, data, execution, gene-mapping and negative-compatibility records;
an E. coli-specific input/output adapter contract; a prepared model input; a local-only adapter;
prepared-bound output validation/projection; deterministic synthetic conformance; and fail-closed
tests. Flux is trace-only and cannot enter the public adapter output.

The exact implementation diff from the starting SHA to the completion code SHA contains four paths:

- praxis_virtualcell/model_zoo/adapter_sdk.py;
- praxis_virtualcell/tests/test_model_adapter_sdk.py;
- praxis_virtualcell/model_zoo/ecoli_growth_contract.py;
- praxis_virtualcell/tests/test_ecoli_growth_contract.py.

The first two paths are the shared SDK trust-boundary prerequisite commit: recursive rejection of
hidden/extra/subtype/dataclass type drift and prepared-aware projection. The second commit adds only
the E. coli contract module and tests. P13 delta adapter/input/output/prepared/envelope/conformance
fingerprints remain byte-for-byte unchanged.

No staged, modified, deleted or untracked paths existed before documentation closure started.
old/**, the three protected repository copies, remote refs, GitHub, .53, services, ports, external
assets and deployment state were not modified.

## Explicitly not performed

P14E did not:

- read, download, deserialize or execute a real GEM, SBML model, growth dataset or essentiality
  dataset;
- import or invoke Cobra, a solver, GemWrapper or textbook-model fallback;
- run test_ecoli_gem_case.py, test_gem_wrapper.py, medium/antibiotic/yeast GEM science tests, or
  Phase 10 real GEM cases;
- create a real Pack, artifact, environment snapshot, model release, benchmark result, validation
  evidence or operator policy;
- update registry.yaml, the default adapter registry, runtime routing, wrappers, model cards or
  product surfaces;
- access network, use LLM/GPU/remote compute, train a model, push, open a PR, modify main/tag,
  release, deploy, operate .53, or restart a service.

P14R remains AUTHORIZATION_REQUIRED / NOT_RUN. P14B remains NOT_RUN.

## Contracts and immutable identities

P14E adds:

- vc.ecoli-growth-scope.v1;
- vc.ecoli-growth-validation-protocol.v1;
- vc.ecoli-growth-data-binding.v1;
- vc.ecoli-growth-execution-binding.v1;
- vc.ecoli-growth-gene-mapping-binding.v1;
- vc.ecoli-growth-compatibility-binding.v1;
- vc.ecoli-growth-adapter-input-contract.v1;
- vc.ecoli-growth-adapter-output-contract.v1;
- vc.ecoli-growth-prepared-model-input.v1.

The adapter-global fingerprints are:

- adapter: 0b26d81c99f3ed216f5dcc6c86814379b6997633c0a6c071109d3ed45918b1a9;
- input contract: 6995a1c262367bbd510a488b80b2c01a15e18cd6c32169f3036045869218edfa;
- output contract: bfda36704cfd82006ec0a3bd1c772d62209eb8c860b7baffae982f150955f13f.

The canonical synthetic fixture fingerprints are:

- artifact: 435f2868ed5e86a7ea1cf5ff47463896213b4cef8f515acd731f30c34d50c283;
- environment: b572089b347346becb09a2915046b8cd6e55c3ba681124e5275d2250c87fa065;
- model release: 03db9b219ea47e954a2b89cdd0fa28c6395235cd28a4b938e6aa63ec0de405ba;
- mapping: c355339c2450214384300aa966de130f42e64d68fa50138d9fae3d6e3fef1886;
- execution: 832eb94872fc2ed09fbbc97368287538ca6673424f5e3928c61fc5f0699dc5ac;
- Pack identity: 5555555555555555555555555555555555555555555555555555555555555555;
- data binding: 93faa211ed040d378d67c82055c00f96c5af5399cf677ca986692b5c323d74a6;
- compatibility: b61c7d6bacf2a2ca2de76d0ced740acef4a548155c9f4e09b7e5fa891ba81878;
- scope: bd7bc1cf60877ee8abfeb2e8769cf1cfd6e99e34305487da09fb18e810fc996e;
- validation protocol: a4b0bcc46aed1586cc5a466d06422753f944043ca526a2c88ceeeef79f3a88dc;
- prepared input: f6b1e7f263fc0b4608fedda71475b66fa0a20e9754dbe27a27d7714730e1f344;
- output envelope: c7ea3e0d8d966bed09008425adc81c018be4643566e0fbe3db7fafbe7b1d6cae;
- conformance report: 608e931a8a2b5199410b15428587ef03b9c5b6bd6b7b8fdf89ab753b1f1a752e.

The synthetic compatibility record is intentionally negative:
assets_verified=false, executable=false, reason=p14r_not_authorized. The validation protocol is a
preregistration contract, not validation evidence. None of the fixture component identities proves
that an external file exists or is licensed, loadable, scientifically correct or promoted.

Frozen source-file SHA-256 values at the completion code commit are:

- adapter_sdk.py: de503fcc11c32fcbc985f23235739bf428ef6d8c400e94aeb46b0e0541448304;
- test_model_adapter_sdk.py: 0acb9df2359c0cf0f8fc0a23c702a772e63ab02eca161b7a791fe3dba87d1968;
- ecoli_growth_contract.py: 0c79d329468d3e85f47b459a5a46f937c82371cb4d9d20f45394df7bedbc5ff9;
- test_ecoli_growth_contract.py: c5f0f85b80fa40b72b60af15979341d173cdf25cf2ccf8e0bb3fa82121818825.

## Validation bound to completion bytes

All validation ran locally without network, external assets, GEM/SBML reads, real weights,
training, LLM, GPU or remote services.

- P14E contract file: 71 passed.
- P14E plus adjacent SDK/output-flow files: 148 passed.
- Safe nine-file directed gate: 360 passed.
- Safe legacy gate: 1147 passed, 58 skipped, 105 deselected.
- Full active-tree Ruff: passed.
- git diff --check: passed.
- Three independent exact-hash adversarial reviews: no P1/P2 findings.
- Adversarial probes covered hidden/excluded/computed Pydantic subtype fields, dataclass subtype and
  MappingAssetRef drift, nested model_copy extras, wrong scope/hash/type/unit/provenance, unsafe load
  policy, OOD/abstain, reserved science/policy output and default-registry isolation.
- P13 frozen adapter/input/output/prepared/envelope/conformance fingerprints: unchanged.

The directed gate used only:

- test_ecoli_growth_contract.py;
- test_model_adapter_sdk.py;
- test_model_adapter_output_flow.py;
- test_capability_runtime.py;
- test_model_registry_v2.py;
- test_request_v2.py;
- test_packaging.py;
- baseline/test_baseline_offline_report.py;
- baseline/test_baseline_routing_snapshot.py.

## Packaging evidence and limitation

Two clean Git archives of the exact completion code commit were built independently with
COPYFILE_DISABLE=1, fixed SOURCE_DATE_EPOCH=1786002407, Python 3.13.12, setuptools 83.0.0 and
wheel 0.47.0. Frontend npm install/build ran offline with OS-level network denial and isolated
temporary caches. The complete release wheels are byte-identical:

- size: 1,086,768 bytes;
- SHA-256: 462b89376a5134906e98ea4b1ec573bc24e5f2e53266d5a7104be8d625eb88b3;
- contents: 14 deterministic React static files, the P14 module and no test tree;
- archive hygiene: no AppleDouble or __MACOSX entries.

A separate Python-only clean-archive wheel was also byte-identical across two builds:
674,254 bytes, SHA-256
0afde0ee18bba80f0f6d48ecfc7eced8e785ab284b8be7d4342ffea195e49ee7.
It is not the full release artifact.

An isolated runtime environment with exact dependency versions passed dependency compatibility,
installed-wheel imports, delta-only default registry, local P14 adapter registration and
no-Cobra checks. The strict one-shot offline --require-hashes install could not be refreshed:
the local uv cache lacked the original wheel bytes/metadata for cffi 2.1.0, rpds-py 2026.6.3,
PyYAML 6.0.3 and pydantic-core 2.46.4. Repacked cache contents have different archive hashes and
were used only for the explicitly limited compatibility smoke. Therefore this report does not claim
a new exact lockfile-integrity proof for P14E. P14E did not change dependency declarations; the
prior P13 hash-locked evidence remains historical and is not relabeled as P14E evidence.

## Engineering, science and policy status

Engineering:

- contract_defined=true;
- implementation_complete=true;
- tests_passed=true;
- default_registry_unchanged=true;
- real_assets_verified=false;
- executable=false.

Scientific evidence:

- state=NOT_RUN;
- benchmark_passed not established;
- scientifically_validated=false;
- promotion_eligible=false;
- no baseline comparison, paired CI, independent cohort or real OOD result exists.

Product policy:

- state=NO_NEW_DECISION;
- production_promoted=false;
- no named operator decision exists.

Release:

- no product/API/runtime version bump;
- no Git tag, push, PR, artifact publication, release or deployment.

## Negative result retained and limitations

The P9 external-validation result remains
abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e;
available=false, scientifically_validated=false and runtime abstention are unchanged.

Known limitations:

- no real E. coli GEM, growth/essentiality dataset, solver execution or scientific result;
- no type-level proof that an arbitrary future GEM loader is data-only;
- no production growth adapter, model release, evidence or policy;
- deterministic FBA uncertainty is declared unavailable and uncalibrated;
- only growth_ratio is contracted; absolute growth, essentiality, expression, resistance and flux
  remain unsupported public outputs;
- P14R needs exact asset paths/hashes/licenses/source/output root/run window authorization;
- P14B needs positive P14R evidence and a named operator.

Next eligible local work unit: P15E — exact S. cerevisiae strain/condition
gene-deletion→fitness contract. It starts from the actual P14E docs-closure commit read from Git
history, not directly from the P14E code commit. P15R and P15B remain separate authorization
windows.
