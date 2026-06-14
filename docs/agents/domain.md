# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

**This repo is single-context:** one `CONTEXT.md` + `docs/adr/` at the repo root.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the project's glossary.
- **`docs/adr/`** — read the ADRs that touch the area you're about to work in
  (0001 lens · 0002 deterministic computation · 0003 decompose by psychic
  structure · 0004 default-blind/Barnum · 0005 RAG depth corpus · 0006
  qualitative-hermeneutic eval · 0007 Claude Code as runtime).

If any of these files don't exist, **proceed silently** — don't flag their
absence. `/grill-with-docs` creates them lazily as terms and decisions resolve.

## Use the glossary's vocabulary

When your output names a domain concept (an issue title, a charter, a hypothesis,
a test name), use the term as defined in `CONTEXT.md` — Native, archetypal
hypothesis, structure agent, depth-critic, interpreter, chart brief, run artifact,
provenance, multivalence, run mode. Don't drift to the synonyms the glossary lists
under `_Avoid_`.

If the concept you need isn't in the glossary yet, that's a signal — either you're
inventing language the project doesn't use (reconsider), or there's a real gap
(note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than
silently overriding:

> _Contradicts ADR-0006 (qualitative-hermeneutic evaluation) — but worth
> reopening because…_
