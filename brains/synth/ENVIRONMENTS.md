# PRAXIS-Synth — Available environments (zkyd@10.102.106.53)

Verified 2026-05-12.

**Status: production binaries not installed.** antiSMASH, iBioSim, RetroPath, BiG-SCAPE, DeepBGC all require their own conda envs (or Java for iBioSim) and have not been provisioned on this host. The 2 env-var refs in code are optional — skills fall back to literature-only / planning mode when binaries are absent.

Web-API skills (CrossRef, NCBI) work out of the box once `NCBI_EMAIL` and `CROSSREF_MAILTO` are set.
