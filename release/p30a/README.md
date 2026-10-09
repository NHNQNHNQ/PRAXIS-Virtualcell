# P30A capability-classification boundary

`capability-classification.json` is a local release-exposure projection, not
an execution registry. Its `authoritative_for_execution` value is `false` and
every record has `prediction_allowed=false`. A runtime must still make its own
exact request × Pack × model × environment × adapter × evidence × policy
decision; this file cannot enable a model or turn an abstention into a result.

The four release classes describe software distribution exposure only. In
particular, the `production` entry is non-predictive Model Zoo infrastructure,
not a biologically `production_promoted` capability. Engineering, science and
policy remain independent projections in each record's `*_status` fields.
There are no scientific-evidence or product-policy fingerprints in this P30A
classification, and the science-qualified badge is deliberately ineligible.

`completion_shas` identify local engineering commits. `source_reports` pin the
current bytes of their completion reports. Any `conformance_fingerprints` are
deterministic regression-fixture identities only; they are not scientific
evidence and must never be copied into `evidence_fingerprints` or
`policy_fingerprints`.

P23B and P24 are intentionally separate unsupported scopes. P23B requires
intervention data, an estimand, assumptions, a frozen protocol and P21B
candidate/evidence identity before a receiver-response claim can be
considered. P24 is a two-member, well-mixed, medium/abundance/time community
scope that requires a new real adapter/version using v2 or an independent
schema; the retained P10 `vc.community-*.v1`
serialization/fingerprint/abstention contract is not that adapter and is not
scientific evidence.
