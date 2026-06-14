# PRD: Natal-chart depth-instrument — v1 sandbox to first runnable dossier

_Triage: **ready-for-agent**. Vocabulary per `CONTEXT.md`; decisions per `docs/adr/0001–0007`._

## Problem Statement

As a Jungian analyst-researcher, I want to study whether an ensemble of LLM
agents can read a natal chart as a *depth-instrument* — surfacing non-obvious,
generative **archetypal hypotheses** about the native that ring true to a trained
ear. The tools that exist do the opposite of what depth work needs: astrology
software and LLM-astrology demos produce **cookbook**, atomized, single-valence
delineations ("Mars in Gemini means scattered energy") — parallel summaries that
never speak to each other, collapse every archetype to one meaning, and read as
Barnum-vague or as retrofits of facts already known. I have no instrument that
(a) decomposes a chart by *structures of the psyche* rather than by celestial
bean-counting, (b) holds **multivalence**, (c) resists the Barnum effect, and
(d) exposes its reasoning so I can contest it. And because the *method* is the
object of study, I need it to live somewhere I can iterate on quickly.

## Solution

A Claude Code-native research **method sandbox**. I supply birth data, a layer
**Selection**, and a **Run mode** (default **blind**). A deterministic in-repo
tool computes an exact **chart brief** (the LLM never does the astronomy). An
orchestrator, following an editable **AGENTS.md brief**, spawns independent
**structure-agent** subagents — each reading the *whole* chart through one
Jungian structure via its **charter**, grounded by retrieval over a curated
**depth corpus**. A **depth-critic** attacks vagueness, Barnum, cookbook
flattening, and non-falsifiability. An **interpreter** synthesizes a holistic
individuation portrait that *holds* the tensions rather than dissolving them. The
run is persisted as a layered, contestable **run artifact** (dossier) with full
**provenance**, and I record a freeform **Reflection** — the sandbox's only
evaluation signal. Because the method is prose (brief + charters), tuning my
research variable is a text edit, not a refactor.

## User Stories

1. As an analyst-researcher, I want to enter a native's birth date, exact time, and place, so that the instrument can cast an accurate chart.
2. As an analyst-researcher, I want birth time and place resolved to precise coordinates and historical timezone/DST, so that house cusps and angles are correct.
3. As an analyst-researcher, I want the chart computed by a real ephemeris (Swiss Ephemeris), so that no planetary position is ever hallucinated.
4. As an analyst-researcher, I want a tropical zodiac and Placidus houses by default, so that the chart matches my psychological-astrology lineage.
5. As an analyst-researcher, I want the ten planets, four angles, lunar nodes, and Chiron as core bodies, so that the structures have their primary significators.
6. As an analyst-researcher, I want optional bodies (Black Moon Lilith, the four asteroids, Part of Fortune) available but off by default, so that I can enrich a run without cluttering the baseline.
7. As an analyst-researcher, I want the five Ptolemaic aspects plus the quincunx with standard orbs, so that the dynamic complexes are detected.
8. As an analyst-researcher, I want configurations (stellium, T-square, grand cross, grand trine, yod, kite) detected as gestalts, so that the chart's archetypal complexes are surfaced as wholes.
9. As an analyst-researcher, I want to select which temporal **layers** are in frame per run (natal, transits, secondary progressions, solar arc, solar return), so that I can read the structural mandala alone or the psyche in developmental time.
10. As an analyst-researcher, I want layer selection at the whole-layer level for v1, so that the knob stays simple while the method is still moving.
11. As an analyst-researcher, I want each selected layer to compute its full standard factor set, so that a selected layer is never silently partial.
12. As an analyst-researcher, I want the computed chart rendered into a structured **chart brief** that every agent reads as ground truth, so that grounding is shared and exact.
13. As an analyst-researcher, I want to run **blind** (birth data only) by default, so that the reading can't quietly echo facts I already know.
14. As an analyst-researcher, I want an optional **contextualized** mode that reads the chart against a native's known biography, so that I can get clinical resonance when that's the goal.
15. As an analyst-researcher, I want the instrument never to *require* the native's gender, so that anima/animus is read as the fluid contrasexual soul-image, not hard-assigned by sex.
16. As an analyst-researcher, I want the chart decomposed by **structures of the psyche**, not by planet/house/aspect, so that I get psychological hypotheses instead of cookbook delineations.
17. As an analyst-researcher, I want a **Shadow** agent reading the disowned/afflicted (Saturn, Pluto, 8th/12th, hard aspects, South Node), so that what the native rejects is named.
18. As an analyst-researcher, I want a **Persona** agent (Ascendant, 1st, MC), so that the adaptive mask is read distinctly from the conscious ego.
19. As an analyst-researcher, I want an **Ego / conscious standpoint** agent (Sun, Mercury, ASC-ruler), so that the hero's conscious position is articulated.
20. As an analyst-researcher, I want an **Anima/Animus** agent (the contrasexual soul-image, read fluidly), so that the inner Other and its projections are surfaced.
21. As an analyst-researcher, I want a **Parental complexes** agent (Moon=mother, Saturn/Sun=father, IC/MC, 4th/10th), so that the foundational imagos are read.
22. As an analyst-researcher, I want a **Wound** agent (Chiron, 12th), so that the place of woundedness and its medicine is named.
23. As an analyst-researcher, I want a **Vocation/telos** agent (MC/10th, Saturn, Jupiter, North Node, 9th), so that the direction of becoming is read.
24. As an analyst-researcher, I want an **Eros/relating** agent (Venus, Mars, 5th/7th/8th), so that desire and intimacy are read as a function distinct from the anima.
25. As an analyst-researcher, I want a **Numinous/transpersonal** agent (Neptune and the outer planets, the religious function), so that the more-than-personal dimension is surfaced.
26. As an analyst-researcher, I want each structure agent to read the *whole* chart through its own **charter** (its single interpretive question), so that two agents looking at the same Moon produce *different* readings.
27. As an analyst-researcher, I want overlap of significators treated as **multivalence**, not duplication, so that the same placement legitimately yields the mother-imago, the soul-image, and the erotic appetite.
28. As the orchestrator, I want each structure agent to receive only its charter plus the chart brief, so that the agents stay independent and genuinely in tension rather than converging on consensus.
29. As an analyst-researcher, I want each structure agent grounded by retrieval over the **depth corpus**, so that its reading is anchored in the Greene/Tarnas/Jung lineage and not generic.
30. As an analyst-researcher, I want amplification material (myth, alchemy, fairy tale) retrievable for a chart's key images, so that readings deepen beyond astrological delineation.
31. As an analyst-researcher, I want the corpus to exclude cookbook delineation tables, so that retrieval can't reintroduce the flattening the instrument resists.
32. As an analyst-researcher, I want a **depth-critic** to attack each structure reading for vagueness, Barnum, cookbook flattening, and non-falsifiability, so that weak claims are challenged before synthesis.
33. As an analyst-researcher, I want the critic to force grounding in *this* chart, so that no claim survives that could apply to anyone.
34. As an analyst-researcher, I want a strong **interpreter** to synthesize the surviving readings into one holistic individuation portrait from the Self vantage, so that I get a coherent whole, not nine essays.
35. As an analyst-researcher, I want the interpreter to *hold* the tensions between structures rather than resolve them into mush, so that the multivalent truth is preserved.
36. As an analyst-researcher, I want the output as a **layered Markdown dossier** — portrait on top, structure readings, critic challenges, and chart brief beneath — so that I get the gestalt and can drill into the contestable substructure.
37. As an analyst-researcher, I want every run persisted as a self-contained **run artifact**, so that I can re-read and compare runs later.
38. As an analyst-researcher, I want each run to auto-capture full **provenance** (selection, run mode, model per role, brief + charter versions, seed, timestamp), so that any judgment is reproducible and attributable.
39. As an analyst-researcher, I want to record a freeform **Reflection** per run (what landed, what was generic/Barnum, what surprised), so that my hermeneutic judgment is the evaluation signal.
40. As an analyst-researcher, I want NO numeric scores or rubrics imposed on a run, so that "good" is never quietly redefined as "scoreable."
41. As an analyst-researcher, I want to read two runs of the same chart side by side, so that I can compare configurations of the method.
42. As an analyst-researcher, I want the whole method (orchestration + charters + critic + interpreter briefs) expressed as editable prose, so that I can tune my research variable with a text edit.
43. As an analyst-researcher, I want to drive a run by pointing Claude Code at the repo's AGENTS.md brief, so that the runtime is the harness I already work in.
44. As an analyst-researcher, I want birth data and computation to stay local, so that an analysand's identifying data never leaves my machine.
45. As an analyst-researcher, I want the deterministic tools runnable on their own, so that I can verify the bedrock independently of the agents.
46. As an analyst-researcher, I want clear failure when birth data is ambiguous or a layer can't be computed, so that I never get a silently wrong mandala.
47. As an analyst-researcher, I want the instrument to run end-to-end even when the corpus is still thin, with agents flagging where grounding was sparse, so that I can produce a first dossier before the full corpus is assembled.
48. As an analyst-researcher, I want the dossier to name which structures spoke and where the critic pushed back, so that I see the seams rather than a smoothed-over synthesis.

## Implementation Decisions

- **Runtime (ADR-0007).** The sandbox is operated by Claude Code, not a standalone program. An **AGENTS.md brief** drives an orchestrator that calls in-repo tools, spawns the structure-agent subagents in parallel, then the depth-critic and the interpreter, and writes the run artifact. `CLAUDE.md` references the brief so the orchestrator reliably loads the method.
- **Modules built/modified:**
  - *Chart-computation tool* — takes birth data + Selection, returns the **chart brief**. Deterministic, Swiss-Ephemeris-backed (kerykeion or immanuel, confirmed at build). Tropical, Placidus, core bodies; optional bodies behind a flag; Ptolemaic aspects + quincunx; configuration detection. The LLM never computes (ADR-0002).
  - *Retrieval tool* — takes a charter/image-scoped query, returns ranked passages from the **depth corpus**; plus an ingestion step that builds a local index. Local embeddings + local vector store (LanceDB / sqlite-vec / Chroma, confirmed at build) for privacy (ADR-0005).
  - *Brief + charter files* — the AGENTS.md orchestration brief; one charter file per structure agent; a depth-critic brief; an interpreter brief. Prose, version-controlled — the live research variable.
  - *Run-artifact writer* — assembles the layered dossier and writes provenance + a reflection scaffold into a per-run directory.
- **Interfaces / contracts:**
  - *Chart brief* — a structured object (machine-readable + a Markdown rendering): per selected layer, bodies with sign/house/degree, aspects with orbs, detected configurations, and the angles. The shared ground truth every agent reads.
  - *Selection* — the set of layers in frame for a run (whole-layer granularity in v1).
  - *Run mode* — blind (default) or contextualized; contextualized additionally accepts a biography input.
  - *Provenance* — selection, run mode, model per role, brief + charter git-SHAs, seed, timestamp.
  - *Run artifact* — a per-run directory: provenance/config, chart brief, one file per structure reading, critic challenges, interpreter portrait, reflection scaffold.
- **Architectural decisions** — recorded as ADRs: committed Greene+Tarnas+Hillman lens (0001); deterministic computation (0002); decompose by psychic structure (0003); default-blind / Barnum-resistance + fluid anima (0004); RAG over a depth corpus, no cookbooks (0005); qualitative-hermeneutic evaluation, no metrics (0006); Claude Code as runtime (0007).
- **Models** — Opus for the interpreter and depth-critic (heaviest synthesis/critique); Sonnet acceptable for the structure agents.
- **Reproducibility** — soft by design (ADR-0007): provenance captures config + prose-version SHAs, not deterministic replay; acceptable because readings are non-deterministic and evaluation is hermeneutic (ADR-0006).

## Testing Decisions

- **What a good test is here:** it asserts on *external behavior* at the highest seam — the chart brief's content, the retrieval results' source-set, the dossier's shape — never on internal calls (kerykeion internals, embedding mechanics, subagent plumbing). The deterministic layer is tested; the interpretive layer is not.
- **Seam 1 — chart brief (golden charts).** Given known birth data, assert the brief's positions, house cusps, aspects (with orbs), and configurations match an authoritative reference within tolerance; tropical+Placidus honored; layer Selection includes/excludes correctly; optional bodies absent by default; angles, nodes, Chiron present. The bedrock and the anchor test pattern for the repo.
- **Seam 2 — retrieval (mechanism + curation invariant).** Assert retrieval returns passages drawn from the indexed depth corpus, and that the index contains **no cookbook delineation tables** (the ADR-0005 curation invariant). Semantic relevance is deliberately *not* asserted — that's hermeneutic.
- **Seam 3 — artifact contract.** Assert a completed run yields a well-formed dossier: provenance fields present; one reading per active structure agent; critic and interpreter sections present; reflection scaffold present. Structural shape only, not content quality.
- **Explicit non-goal:** the interpretive *quality* of structure readings, critic, and portrait is judged by the analyst's **Reflection**, not by automated tests or metrics (ADR-0006). Adding quality metrics is out of scope and against the methodology.
- **Prior art:** none — greenfield. These three seams establish the testing pattern; the golden-chart tests are the canonical example future deterministic tests follow.

## Out of Scope

- **Sourcing the depth-corpus texts** (the analyst's reading list / Calibre extraction) — a user-supplied input. v1 ships the ingestion pipeline + retrieval and runs end-to-end with a thin seed, flagging sparse grounding.
- **Factor-level / cross-layer selectors** — v1 is whole-layer only (designed to extend later).
- **Pairwise comparison** tooling and **inline annotation** evaluation — the planned next eval step (ADR-0006); v1 ships reflective notes + provenance only.
- **Synastry** (two-chart relational analysis) — a distinct sub-instrument.
- **Sidereal zodiac** and non-Placidus house systems — conceptually configurable, but v1 defaults only.
- **Cookbook RAG** and **live web amplification** — the former rejected (ADR-0005), the latter deferred.
- **Polished, client-facing report styling** — output polish is explicitly secondary; v1 optimizes for contestability and provenance.
- **A bespoke UI / web service** — the runtime is Claude Code + in-repo tools; there is no separate app.

## Further Notes

- **Anima/animus stance (ADR-0004):** read fluidly as the contrasexual soul-image, independent of the native's sex/orientation; supplied gender informs but never hard-assigns. A deliberate deviation from classical Jung — flagged for the analyst to override before the charters are finalized if their clinical view differs.
- **Highest-leverage input:** the corpus reading list. The instrument's depth tracks the quality of the curated texts.
- **CLAUDE.md → AGENTS.md wiring:** Claude Code reads `CLAUDE.md` natively; the brief must be referenced from it so the orchestrator loads the method.
- **Privacy:** computation and embeddings are local; birth data never leaves the machine; the repo is private and contains only design/method docs and code — no analysand data.
- **Glossary:** every bolded term is defined in `CONTEXT.md`; this PRD uses that vocabulary deliberately.
