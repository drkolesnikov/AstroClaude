# Natal Chart Method Sandbox

This repository is a Claude Code-native research sandbox. The orchestration brief
lives in `AGENTS.md` — **load it before performing an end-to-end run**. It tells
you how to compute the chart, retrieve depth-corpus grounding, fan out the
structure agents, write the critic section, run the interpreter, record
Reflection, compare runs, and assemble the dossier.

The deterministic boundary is the main rule: use the in-repo `compute_chart` tool
to produce the exact chart brief, and never ask an LLM to compute planetary
positions, houses, aspects, or configurations.
