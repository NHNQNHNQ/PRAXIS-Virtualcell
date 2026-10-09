---
rule_id: 01-output-formatting
schema_version: 1
rule_type: output_format
scope: global_presentation
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# Output presentation

Use English for public answers. Use standard Markdown tables with a header and
separator row when comparing methods. Choose useful decision criteria: task and
data applicability, limitations, resources, benchmark results, and availability.
Include citations with the claims they support.

Explain the recommendation for the current task after the comparison. Short
parallel facts can use a list. Keep commands, code, and raw logs in code blocks.
Use smaller grouped tables when a single table would be too wide.
