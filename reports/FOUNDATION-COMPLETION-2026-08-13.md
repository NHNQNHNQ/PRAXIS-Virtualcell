# PRAXIS-VirtualCell Foundation Completion — 2026-08-13

## Outcome

The software and data foundation is complete for one real, explicitly scoped research workflow:

1. exact omics bytes enter quarantine and receive a hash-bound upload receipt;
2. an operator records that receipt in a local Pack Factory;
3. an operator-authored H5AD/H5MU Pack can become a candidate, receive explicit metadata review,
   deterministic validation, an operator decision, and registration;
4. compatibility is evaluated against an exact request, Pack, model, environment, adapter, evidence,
   and policy identity;
5. the UI discovers the registered AHR+KLF1 Norman task from the configured server, previews the
   same runtime plan, requires explicit confirmation, and executes only while that preview remains
   current;
6. persisted results expose Pack, model, research scope, and scientific status without local paths.

The public HTTP Pack Factory remains read-only. Authoring, review, approval, and registration are
operator-local actions. Uploading data does not infer biological metadata, approve a Pack, register a
model, or make anything executable.

## Current real research capability

The checked-in Golden additive release is artifact-ready and authorized only for the exact Norman
K562 AHR+KLF1 CRISPRa request. Its execution scope is `research_only`.

Authoritative release state:

| Field | Value |
|---|---|
| `benchmark_passed` | `false` |
| `scientifically_validated` | `false` |
| `promotion_eligible` | `false` |
| `production_promoted` | `false` |

The GSE220974 analysis is a passed, locally prespecified external stress test of the underlying
additive baseline algorithm. It is not an exact P16 external gate, a P21 benchmark result, or evidence
for the full registered Direct-v2 release scope.

## GEARS candidate status

The repository contains the train-only protocol, contamination boundary, three-seed 20-epoch
execution contract, validation-only truth contract, and frozen evaluator design. At this snapshot the
candidate set is still pending freeze and no Golden validation result is checked in. Therefore:

- benchmark status is `NOT_RUN` / `null`;
- science, promotion, and production remain `false`;
- no Golden test expression or outcomes are authorized by this completion record.

## What “complete” means here

“Foundation complete” means the product can ingest exact omics bytes, govern Pack creation, discover
and run one real research-only model, persist its provenance, and fail closed when identities drift.
It does not mean a general Virtual Cell, a science-qualified release, or a production-promoted model.

Future scientific state changes require new immutable candidate, validation, benchmark, external
evidence, and operator-policy identities. They must not rewrite this record or the existing Golden
research release.
