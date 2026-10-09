# Versioning

The product version is declared in `pyproject.toml` and mirrored by the CLI, API, and frontend.
Data schemas, model and adapter contracts, environment identities, and evidence artifacts
have independent versions. These identities are recorded in execution provenance.

A software release does not promote a model's scientific or product status. Compatibility
and validation gates apply to the exact recorded artifact scope. Public schema changes
must document compatibility or provide a migration path.
