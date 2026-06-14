# Natal Chart Method Sandbox

This repository is a Claude Code-native research sandbox. The orchestration brief
lives in `AGENTS.md` — **load it before performing an end-to-end run**. It tells
you how to compute the chart, fan out the structure agents, write the critic
section, run the interpreter, record Reflection, compare runs, and assemble the
dossier.

The deterministic boundary is the main rule: use the in-repo `compute_chart` tool
to produce the exact chart brief, and never ask an LLM to compute planetary
positions, houses, aspects, or configurations.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `drkolesnikov/natal-chart` (via the `gh` CLI). See
`docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map 1:1 to same-named labels; the lane labels
`model:opus` / `model:gpt-5.5` route an issue to a model. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See
`docs/agents/domain.md`.
