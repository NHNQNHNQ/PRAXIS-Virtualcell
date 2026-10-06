# Agent brains and tool rules

- [`virtualcell/`](virtualcell/metadata.yaml) is the default compatibility slug for antibacterial candidate assessment.
  Its runtime rules are in [`memory/rules/`](virtualcell/memory/rules/01-antibacterial-assessment.md);
  [`prompts/system.md`](virtualcell/prompts/system.md) is the editable role reference.
  The current loader retrieves memory rules/cases and reads metadata for the profile; it does not inject `prompts/` directly.
- `_common/` contains the shared retrieval, docking and tool execution rules for the retained praxis2 agent runtime.
- Antibacterial species rules are packaged under `praxis_virtualcell/mdr_gnb/agents/*/brain/`.
- Historical mammalian virtual-cell brains are in the external archive.
