# Testing

These checks cover the standalone 1.0.0 scientific runtime and its applications.
Run them from the repository root. Use an isolated environment and install
the development dependencies:

```bash
python -m pip install -e ".[dev,api,mechanistic,omics]"
python -m pip check
ruff check .
```

Python 3.13 dependency locks are documented in
[requirements/README.md](../requirements/README.md).

## Standalone VirtualCell tests

```bash
pytest praxis_virtualcell/tests \
  -m "not (integration or llm or remote)" -o addopts='' -q -ra
```

For a focused change, run the affected tests first. Scientific fixtures and
mock predictors verify software contracts; their success is software evidence.

## Frontend checks

```bash
cd praxis_vc_react
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

Playwright requires its browser installation for end-to-end checks.

## External checks

External tests require explicit opt-in and the appropriate local prerequisites.

| Marker | Enable with | Prerequisites |
|---|---|---|
| `integration` | `--run-integration` | The required service, container, or dependency |
| `llm` | `--run-llm` | Provider configuration and credentials |
| `remote` | `--run-remote` | The exact model assets, checkpoint, GPU, or remote service |

If a test has multiple markers, each corresponding opt-in must be enabled.
Ordinary local checks do not establish scientific validation or model promotion.
For research evaluation protocols, use [reproducibility](REPRODUCIBILITY.md).

[Documentation](INDEX.md) · [Installation](INSTALL.md)
