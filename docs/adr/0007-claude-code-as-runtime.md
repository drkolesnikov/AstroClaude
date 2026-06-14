# Claude Code is the runtime: an AGENTS.md brief + parallel subagents + in-repo tools

The sandbox is not a standalone program — it is **operated by Claude Code**. A
natural-language **AGENTS.md brief** drives an orchestrating agent that: invokes
**in-repo Python tools** for the deterministic layer (Swiss-Ephemeris chart
computation → chart brief; depth-corpus retrieval); spawns the structure agents
as **independent parallel subagents**, each fed only its charter
(`agents/<structure>.md`) plus the chart brief; runs the depth-critic and
interpreter as further passes; and writes the layered run artifact. The
orchestration logic lives as editable prose and charter files, not code.

We chose this because the sandbox's central research variable *is* the
decomposition (roster, charters, critic, interpreter). Expressing the method as
prose briefs makes tuning it a text edit, not a refactor — the fastest possible
iteration on the thing under study. Independent subagents (vs one agent
role-playing every structure in shared context) preserve the genuine tension
between structures the design depends on.

## Considered options

- Thin custom Python orchestration on the Anthropic SDK.
- An agent framework (LangGraph / PydanticAI / CrewAI).
- A Claude Code Workflow (JS) script — most deterministic, but encodes the method
  in code rather than malleable prose.

All rejected in favour of in-harness, prose-driven orchestration for iteration speed.

## Consequences / trade-offs

- **Reproducibility is softer** than coded orchestration: the agent's path
  varies. Provenance captures config + brief/charter git-SHAs + model, but not
  deterministic replay — acceptable because readings are non-deterministic LLM
  output regardless, and ADR-0006 already makes evaluation hermeneutic, not metric.
- The deterministic guarantees of ADR-0002 (computation) and ADR-0005
  (retrieval) are **preserved by keeping that work in code** (the in-repo tools);
  the LLM still never computes.
- Claude Code reads `CLAUDE.md` natively; the `AGENTS.md` brief must be
  referenced from `CLAUDE.md` (or Claude Code configured to read it) so the
  orchestrator reliably loads the method.
