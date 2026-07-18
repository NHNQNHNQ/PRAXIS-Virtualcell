# Python 3.13 dependency locks

`pyproject.toml` defines the supported compatibility ranges. These generated
files freeze the resolver result used by CI and release validation:

- `runtime-py313.lock`: core plus the `api` extra used by the local API and
  production container.
- `dev-py313.lock`: core plus `dev`, `api`, `web`, and `mechanistic`, used by
  the complete local/CI test environment.

Install the locked dependencies before installing the project itself without
dependency resolution:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements/dev-py313.lock
.venv/bin/python -m pip install --no-deps -e .
```

Regenerate only with Python 3.13 and the pinned compiler version:

```bash
python3.13 -m venv /tmp/praxis-lock-tools
/tmp/praxis-lock-tools/bin/python -m pip install pip-tools==7.5.3
/tmp/praxis-lock-tools/bin/pip-compile pyproject.toml \
  --extra api --generate-hashes --resolver backtracking --strip-extras \
  --output-file requirements/runtime-py313.lock
/tmp/praxis-lock-tools/bin/pip-compile pyproject.toml \
  --extra dev --extra api --extra web --extra mechanistic \
  --generate-hashes --resolver backtracking --strip-extras \
  --output-file requirements/dev-py313.lock
```

The locks are interpreter-specific. Python 3.11/3.12 still follow the bounded
metadata contract, but must not be described as locked until separately
generated and tested lock files exist.
