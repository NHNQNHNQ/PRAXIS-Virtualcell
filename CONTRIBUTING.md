# Contributing

PRAXIS-VirtualCell accepts changes that preserve its fail-closed product contract: data may be packaged under
explicit schemas, but prediction requires exact compatible, scientifically validated, product-promoted model
scope. A passing schema or synthetic fixture is not scientific evidence.

## Local workflow

1. Create a focused branch from the intended immutable baseline.
2. Keep data, model, environment, adapter, evidence and policy identities explicit.
3. Add negative tests before or with implementation; unsupported and stale inputs must abstain.
4. Run the directed tests, Ruff, frontend checks when affected, packaging/versioning tests and `pip check`.
5. Update the relevant ADR, runbook, versioning table and status ledger without upgrading science or policy.

Do not commit secrets, private paths, raw external datasets, checkpoints, model weights or generated release
artifacts. External data/model runs, operator promotion, push, release and deployment use separate approvals.

Pull requests should state exact scope, non-goals, tests, immutable identities, negative results, scientific
status, product-policy status and rollback implications. Changes to a public schema require a new version or an
explicit compatibility/migration path.
