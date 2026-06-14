# Natal Chart Method Sandbox

This repository is a Claude Code-native research sandbox. The full orchestration
brief will live in `AGENTS.md`; when that file exists, load it before attempting
an end-to-end run.

For now, the deterministic boundary is the main rule: use the in-repo
`compute_chart` tool to produce the exact chart brief, and never ask an LLM to
compute planetary positions, houses, aspects, or configurations.
