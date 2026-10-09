# Contributing

Contributions to the virtual-cell runtime, model adapters, agent framework, and interface are welcome.
Start from `main`, keep changes focused, and describe the resulting behavior in your pull request.

## Development

Follow [the installation guide](docs/INSTALL.md) and run the relevant checks in
[the testing guide](docs/TESTING.md). Include regression tests for changes to runtime behavior.
Frontend changes should also pass TypeScript, lint, build, and the affected browser tests.

Preserve explicit data, model, adapter, environment, and evidence identities. A schema-valid
package or synthetic fixture does not establish scientific validity. Unsupported requests,
incompatible assets, and missing validation evidence must retain their abstention behavior.
LLMs may interpret requests and explain artifacts; predictions and final governance decisions
belong to the deterministic runtime.

Do not commit credentials, private paths, raw external datasets, checkpoints, or generated builds.
Document the source and license of new assets. Public schema changes need a versioned
compatibility or migration path. Cite the [preprint](https://arxiv.org/abs/2609.29221v1)
when discussing the framework in publications.
