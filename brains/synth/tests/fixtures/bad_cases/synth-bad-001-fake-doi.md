---
case_id: synth-bad-001-fake-doi
task: flux_balance_analysis
host_organism: E. coli K-12 MG1655
tools: [COBRApy]
key_paper_doi: 10.9999/this.doi.is.completely.fake.invented.2099
status: validated
---

# Bad case 1: fake DOI

## Background
This case has a deliberately fabricated DOI to verify CrossRef rejection.

## What I actually did
Nothing real — adversarial fixture.

## ★ 排除/不做的事
- Cite fake DOIs

## ★ 失败模式
- DOI fabrication is the failure mode being tested
