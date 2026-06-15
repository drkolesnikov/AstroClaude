# The run artifact owns its layout: a RunArtifact module with a declarative parts table

**Status: accepted and implemented** — shipped as `src/natal_chart/run_artifact.py` in PR #51 (merged to `main`). The record below is the decision and its now-realized shape; see _Outcome_ at the end.

The **run artifact** (CONTEXT.md) is a directory whose layout — which files exist
(`provenance.json`, `chart-brief.md`, `structure/<slug>.md`, `grounding/<slug>.md`,
`critic.md`, `interpretation.md`, `fabrication-report.md`, `reflection.md`,
`dossier.md`, …), which of them are **required** for a valid run, and the **order**
they compose into the dossier — is today re-encoded as roughly fifty path literals
across nine functions: `init_run`, `write_fabrication_report`, `assemble_dossier`,
`validate_run`, `compare_runs` and their helpers in `run.py`, plus the two grounding
writers in `retrieve.py`. No module owns it. Apply the deletion test and nothing
concentrates — the contract is vapor, smeared across call sites; adding one run file
means hand-editing four functions and the `AGENTS.md` prose and hoping you caught
them all.

We will concentrate the Python arm of this contract behind a single deep module,
**`RunArtifact`** (`natal_chart/run_artifact.py`), that owns the layout as a
**declarative table**. Each `ArtifactPart` row carries its relative path, whether it
is required, whether it is a per-structure **family** (`structure/{slug}.md`,
`grounding/{slug}.md`), and its dossier order + heading. `validate()` and
`assemble()` *iterate the table* — required-but-missing parts (families expanded over
the active roster) are the contract failure; order-bearing parts compose in order —
instead of restating the file set in each function body. `scaffold()` writes the
deterministic parts. The existing five functions survive as one-line delegations, so
`AGENTS.md` and the current tests stay green.

`RunArtifact` **materializes the existing "Run artifact" term** — it adds no new
domain vocabulary. It is a stateless wrapper over the run directory, reconstructible
as `RunArtifact(run_dir)` on each separate `python -c` invocation, preserving the
separate-process orchestration model of ADR-0007 (it holds no cross-call state).

We chose this for **locality** — the layout, the required-set, and the compose-order
live in one declarative place; adding a run file is one table row, not edits to four
functions plus prose — and for **leverage**: callers say `artifact.dossier_path` and
`artifact.structure_reading(slug)`, not `run_dir / "dossier.md"`. The **interface
becomes the test surface**: a scaffold → write → validate → assemble round-trip
exercises the contract directly, instead of poking filenames across five functions.

## Considered options

- **Pure layout value object** — `RunArtifact` owns only the path strings; the
  functions keep their IO logic and ask it for paths. Concentrates the literals but
  leaves the required-set and compose-order spread across `validate`/`assemble`.
  Rejected as too shallow — it moves the strings without giving the contract a home.
- **Full migration** — delete the five functions, rewrite the `AGENTS.md` Python
  snippets and every test against the `RunArtifact` API. Cleanest end state, but the
  largest blast radius on `run.py`, the known collision seam (below). Rejected for
  risk; the thin facade reaches the same depth without the churn.
- **Typed accessors + explicit logic** instead of a declarative table — a method per
  part, with `validate`/`assemble` written as explicit code. Conventional and
  type-safe, but the required-set and dossier order stay encoded in method bodies
  rather than one data structure. Rejected: the table is the deeper concentration;
  typed accessors are kept as an ergonomic wrapper *over* it.
- **Grounding left in `retrieve.py`** — `RunArtifact` owns the core artifact and only
  exposes the grounding directory. Rejected: it preserves the split ownership we are
  removing. `RunArtifact` owns **all** run-directory paths, including `grounding/`;
  the grounding writers depend on it as writers into the artifact.

## Consequences / trade-offs

- **The `AGENTS.md` prose arm is not absorbed.** Structure agents are told literal
  paths to write to (via the file tool, not Python), so the orchestration brief still
  names `structure/<slug>.md` and friends. This decision concentrates the **Python**
  arm (nine functions → one module); `AGENTS.md` remains the single prose place.
  Keeping the two in step is a residual obligation — a later step could have the brief
  quote `RunArtifact`-reported paths.
- **`validate()` needs the active structure roster from provenance / `RunSpec`**, not
  a directory glob — otherwise a structure agent that never wrote its reading cannot
  be flagged as a missing required part. Confirm the roster is recorded in provenance
  before relying on family-expansion; record it there if not.
- **Implementation is deferred by design.** `run.py` is the seam where `codex/*` and
  `claude/*` slice-PRs collide; a whole-module refactor must land as one focused PR
  while `run.py` is quiescent, not stacked on in-flight work (e.g. the rendered-dossier
  step). This ADR records the shape so the eventual change is mechanical and review is
  about placement, not design.
- **ADR-0002 and ADR-0007 are preserved.** The deterministic tools and the
  separate-invocation orchestration are unchanged; `RunArtifact` adds no computation
  and holds no cross-call state.
- **Composes with the sibling deepening.** The architecture review's other `Strong`
  candidate — giving `ChartBrief` queryable fact accessors and deleting the
  `to_markdown()` → regex round-trip in `fabrication.py` — is independent but
  complementary: once `RunArtifact` owns the *files*, `ChartBrief` owning the *facts*
  removes the last place code re-derives a contract from rendered text. Out of scope
  here; recorded as the natural follow-on.

## Outcome

Implemented in PR #51 (`codex/issue-46-runartifact-layout`), landed as one focused PR
while `run.py` was quiescent — exactly as the deferral above prescribed.

- The deep module shipped as `natal_chart/run_artifact.py`: `RunArtifact`, the
  `ArtifactPart` dataclass, and the declarative `LAYOUT` table. `init_run`,
  `write_fabrication_report`, `assemble_dossier`, `validate_run`, and `compare_runs`
  keep their signatures and delegate to it; `retrieve.py`'s grounding writers resolve
  `grounding/<slug>.md` and `grounding/amplification.md` through it.
- `LAYOUT` encodes the dossier order as data — Individuation Portrait, Structure
  Readings, Fabrication Guard, Critic Challenges, Chart Brief, Reflection — and
  `family` is a tag (`"structure"` / `"grounding"`) rather than a bool, so the two
  slug-expanded families are distinguished in a single field.
- `validate()` expands the structure family over `provenance["structures"]`, the
  roster recorded at scaffold time — the dependency flagged above, confirmed present.
- The new interface is exercised directly by `tests/test_run_artifact_layout.py`; the
  prior `tests/test_run_artifact.py` regression net stayed green. A follow-up, PR #50,
  fixed a duplicate critic check surfaced in `RunArtifact.validate`.
- The sibling deepening has also landed: `ChartBrief` owns its facts and the
  fabrication guard reads structure, not rendered Markdown (#43 / #44).
