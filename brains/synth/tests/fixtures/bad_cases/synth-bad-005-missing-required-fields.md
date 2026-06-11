---
case_id: synth-bad-005-missing-required-fields
tools: [COBRApy]
status: validated
---

# Bad case 5: missing required frontmatter

Missing `task`, `host_organism`, and `key_paper_doi` — schema layer should reject.

## ★ 排除/不做的事
- Submitting cases without required frontmatter

## ★ 失败模式
- Schema drift without validation
