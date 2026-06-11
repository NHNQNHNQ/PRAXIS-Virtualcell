---
name: auto_md_submit
host_env: praxis-md
---

# auto_md_submit · SKILL.md

**Version**: v1.27 (2026-05-13)
**Agent**: PRAXIS-MD
**Type**: real-tool wrapper (back-channel API)

## Purpose

Let the PRAXIS-MD agent submit a real GROMACS run to the hipeson cluster
*directly* during chat, without needing the user to leave the chat and use
the /md panel upload form.

## Inputs

| Arg     | Required | Description                                              |
|---------|----------|----------------------------------------------------------|
| --mdp   | yes      | Path to `.mdp` file (run params)                         |
| --gro   | yes      | Path to `.gro` file (initial coords)                     |
| --top   | yes      | Path to `.top` file (topology)                           |
| --itp   | optional | Extra `.itp` / `.ndx` file paths (repeatable)            |
| --note  | optional | Human-readable run description (shown in /md panel UI)   |
| --target| optional | Default `hipeson` (only target supported)                |
| --json  | flag     | Print result as JSON (else human-readable)               |

## Auth

Reads `PRAXIS_AGENT_TOKEN` from env. The token is injected by the web's
chat_stream handler into the hermes subprocess env each turn; TTL 1 hour;
single-use per chat turn is fine. **Do NOT echo the token to the user.**

## Outputs (human-readable)

```
✅ submitted to hipeson cluster
   run_id:        20260513_044501_abc123
   status:        queued
   bundle counts: {'mdp': 1, 'gro': 1, 'top': 1, 'itp': 0}
   remote only:   True  (轨迹留远端, .log 会回来)

用户查看: /md 面板 → run 20260513_044501_abc123
用户下载产物: 点 /md 面板上的 '下载' 按钮 (on-demand scp)
```

## Exit codes

| Code | Meaning                                           |
|------|---------------------------------------------------|
| 0    | Submit OK                                         |
| 1    | Missing input file                                |
| 2    | `PRAXIS_AGENT_TOKEN` not set (not in chat subproc) |
| 3    | HTTP/network error to /api/md/agent-submit       |
| 4    | Inline content > 5 MB cap                         |

## Hard rules for PRAXIS-MD agent

1. **Always confirm with user before submit**: this kicks off real GPU
   compute and bills wall-clock time. Show the user the mdp params + time
   estimate, ask "run? (yes/no)". Only call this skill on explicit yes.
2. **Pass a meaningful --note**: e.g. `"lysozyme NVT 100ps with TIP3P"`.
   It appears in the /md panel and helps users tell runs apart later.
3. **After submit, return the run_id** so the user can check status in /md.
4. **Don't poll**: this skill submits; the agent does NOT wait for results.
   For status, tell user to refresh /md panel or check `/api/md/status/<run_id>`.

## Validation

```bash
# end-to-end with a tiny vacuum lysozyme system:
python3 runner.py --mdp test/run.mdp --gro test/system.gro --top test/system.top --note "test"
# expect: exit 0, run_id printed
```

## v0.2 plans (not in v1.27)

- streaming progress: agent's chat can show "queue position: 2/6 → running on hipeson@.18 → ETA 8m"
- post-run summary: skill helper that fetches the .log via SSH and extracts
  key metrics (temperature settled? did mdrun complete? RMSD trend?)

## 输出契约

```json
{
  "ok": true,
  "skill_id": "auto_md_submit",
  "result": {},
  "diagnostics": {
    "brain": "md",
    "archetype": "generic"
  }
}
```
