---
rule_id: 03-mcp-tools-catalog
schema_version: 1
rule_type: tool_routing
scope: mcp_tool_routing
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# Generic MCP tools

Configured MCP tools use `mcp__<server>__<tool>` names. The bundled BioDB server
queries PubMed, UniProt, PDB, ChEMBL, and PubChem through their public APIs.
Start it with `python -m praxis2.mcp.servers.biodb_server` when configuring an MCP
connection. Additional servers must be configured explicitly.

Retrieve local cases and rules with BrainQuery, verify external records with
BioDB, and use applicable skills for execution. A database response or task
descriptor does not establish that an analysis has completed. Report only tool
results and evidence actually obtained during the task.
