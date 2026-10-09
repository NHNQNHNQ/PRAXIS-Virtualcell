# Python 3.13 dependency locks

`pyproject.toml` defines the supported compatibility ranges. These generated
files freeze the resolver result used by CI and release validation:

- `build-py313.in` / `build-py313.lock`: exact setuptools, wheel, and their
  build-time dependency. Release wheels install this hash lock and use
  `--no-build-isolation`, preventing an implicit second PEP 517 resolution.
- `runtime-py313.lock`: core plus the `api` extra used by the local API and
  production container.
- `dev-py313.lock`: core plus `dev`, `api`, `web`, `mechanistic`, and `omics`, used by
  the complete local/CI test environment. The `dev` extra explicitly includes
  `greenlet` and `watchdog` so the shared macOS arm64/Linux x86_64 lock also
  pins SQLAlchemy's architecture-marked and Streamlit's non-Darwin dependencies
  instead of failing hash mode on GitHub runners.
  The `omics` extra includes AnnData plus MuData 0.3.10; MuData's declared
  compatibility range resolves `scverse-misc` to 0.1.1 in this lock. Neither
  MuData nor scverse-misc is added to the lean runtime lock.
  If another OS or architecture is added, compile and validate a platform-specific
  lock instead of assuming that this two-platform dependency closure is complete.

Install the locked dependencies before installing the project itself without
dependency resolution:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: \
  --require-hashes -r requirements/build-py313.lock
.venv/bin/python -m pip install --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
```

Regenerate only with Python 3.13 and the pinned compiler versions. pip 25.3
preserves the internal API required by pip-tools 7.5.3:

```bash
python3.13 -m venv /tmp/praxis-lock-tools
/tmp/praxis-lock-tools/bin/python -m pip install pip==25.3 pip-tools==7.5.3
/tmp/praxis-lock-tools/bin/pip-compile requirements/build-py313.in \
  --allow-unsafe --generate-hashes --strip-extras \
  --output-file requirements/build-py313.lock
/tmp/praxis-lock-tools/bin/pip-compile pyproject.toml \
  --extra api --generate-hashes --resolver backtracking --strip-extras \
  --output-file requirements/runtime-py313.lock
/tmp/praxis-lock-tools/bin/pip-compile pyproject.toml \
  --extra dev --extra api --extra web --extra mechanistic --extra omics \
  --generate-hashes --resolver backtracking --strip-extras \
  --output-file requirements/dev-py313.lock
```

The locks are interpreter-specific. Python 3.11/3.12 still follow the bounded
metadata contract, but must not be described as locked until separately
generated and tested lock files exist.
