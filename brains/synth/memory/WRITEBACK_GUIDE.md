# Memory writeback guide

Rules of the road for adding to PRAXIS-Synth memory.

## Cases (`memory/cases/synth-NNN-*.md`)

1. **Frontmatter** must follow `_template.md`. `case_id`, `task`, `host_organism`, `status`, `key_paper_doi` are required.
2. **DOI must be CrossRef-resolvable** (`scripts/distill/qa.py --layer doi_crossref` checks).
3. **Mandatory body sections**: `★ 排除` and `★ 失败` — never empty. "未报道" / "无" is acceptable when literature is silent, but the section must exist.
4. New cases land in `memory/cases/_proposed/` and only move to `memory/cases/` after `python scripts/distill/qa.py --strict --case <path>` passes.
5. After adding, update `memory/index.json::cases[]` (script: `python scripts/distill/promote.py --rebuild-index`).

## Rules (`memory/rules/*.md`)

| `rule_type` | Required evidence | Where it lives |
|---|---|---|
| `case_distilled` | `evidence_cases` ≥ 2 | `memory/rules/NN-{slug}.md` |
| `landscape` | broad domain summary; no per-case evidence | `memory/rules/task-overviews/{synth_task}.md` |
| `cold_start_defaults` | none — bootstrap only | `memory/rules/_default_bootstrap.md` |

`applies_to` keys: `synth_tasks`, `host_organisms`, `scale` (use `[ALL]` to match anything).

## Promotion of case-derived seed → rule

Trigger: a "Lessons → seeds" entry appears across ≥ 2 cases. Run:

```bash
python scripts/distill/promote.py --candidate <seed-id>
```

The promoter checks evidence count, applicability boundary, and conflict with existing rules. Reviewer-blocked rule changes go to `memory/rules/_proposed/` for human review.

## Schema versioning

`memory/index.json::schema_version` is bumped when frontmatter required fields change. Past cases are migrated by `scripts/distill/migrate.py`.
