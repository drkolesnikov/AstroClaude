# Orchestration Brief — Natal-Chart Depth Instrument

This is the brief the orchestrating Claude Code agent follows to perform one
**run**. The runtime is Claude Code itself (ADR-0007): you call deterministic
in-repo tools, spawn the structure agents as independent subagents, run the
interpreter, and assemble the dossier. You never compute chart positions yourself
(ADR-0002), and you never collapse an archetype to a single meaning (multivalence,
ADR-0001).

**Current capability:** the full nine-agent roster (Ego, Persona, Shadow,
Anima/Animus, Parental, Wound, Vocation, Eros, Numinous) and the **depth-critic**,
with **blind** and **contextualized** run modes, run provenance, a Reflection
scaffold, and side-by-side comparison of two runs. The natal layer is the default;
other layers are available via `ChartSelection`. Agents retrieve scoped grounding
from the local **depth corpus** before reading; if the corpus is thin, they flag
sparse grounding and continue rather than blocking the run.

## A run, end to end

### 1. Inputs
- `BirthData` (date, time, place).
- **Selection** — whole chart layers, e.g. `["natal"]` or
  `["natal", "transits"]`.
- **Run mode** — `blind` by default, or `contextualized` with a biography input.
  In blind mode you are given **no** biography and must not invent one
  (Barnum-resistance, ADR-0004).
- A short `native` slug (e.g. `ada-lovelace`) for the run directory.
- Optional `seed` for provenance.
- A depth-corpus index. Its location resolves from `$NATAL_CORPUS_INDEX` (a
  **stable path that survives worktree isolation**), falling back to
  `corpus/index/`. **Pre-flight (before Step 4):** confirm `corpus.sqlite` exists
  there. If it does not, announce **"UNGROUNDED RUN — corpus index not found"** at
  the top of the run and require every agent to declare it is reasoning without
  corpus grounding. Never let a corpus-less run pass silently.

### 2. Compute the chart + scaffold the run — deterministic, never by hand
Generate a timestamp (`date -u +%Y-%m-%dT%H:%M:%SZ`) and revision
(`git rev-parse --short HEAD`), then:

    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart import BirthData, ChartSelection, compute_chart
    from natal_chart.run import RunSpec, init_run
    brief = compute_chart(
        BirthData(date="1815-12-10", time="12:00", place="London, GB"),
        selection=ChartSelection(layers=("natal",)),
    )
    spec = RunSpec(
        native="ada-lovelace",
        structures=["ego", "persona", "shadow", "anima-animus",
                    "parental", "wound", "vocation", "eros", "numinous"],
        selection=["natal"],
        run_mode="blind",
        models={"structure": "sonnet", "interpreter": "opus"},
        seed=1234,
    )
    run_dir = init_run(spec, brief, runs_root=Path("runs"),
                       timestamp="<TIMESTAMP>", revision="<REVISION>",
                       charter_root=Path("agents"))
    print(run_dir)
    PY

This writes `runs/<native>-<ts>/` with `provenance.json`, `chart-brief.json`,
`chart-brief.md`, `reflection.md`, and an empty `structure/`. A contextualized
run additionally writes `biography.md`; pass `run_mode="contextualized"` and
`biography="..."` to `RunSpec`.

### 3. Read the ground truth
Read `runs/<run>/chart-brief.md`. This — and only this — is the chart. Every agent
reads it; nobody recomputes it.

### 4. Retrieve charter-scoped grounding
Prepare one grounding file per structure agent from the local depth corpus. Choose
key images from the chart brief (dominant configurations, hard aspects, angular
planets, repeated signs/houses, and any temporal-layer images in Selection).

    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart.retrieve import resolve_index_dir, write_agent_grounding, write_amplification_grounding

    run_dir = Path("runs/<native>-<ts>")
    structures = ["ego", "persona", "shadow", "anima-animus",
                  "parental", "wound", "vocation", "eros", "numinous"]
    key_images = ["<chart image>", "<chart image>"]

    write_agent_grounding(
        run_dir=run_dir,
        index_dir=resolve_index_dir(),  # $NATAL_CORPUS_INDEX or corpus/index
        charter_root=Path("agents"),
        structures=structures,
        key_images=key_images,
        min_results=2,
    )

    write_amplification_grounding(
        run_dir=run_dir,
        index_dir=resolve_index_dir(),  # $NATAL_CORPUS_INDEX or corpus/index
        key_images=key_images,
        top_k=5,
        min_results=1,
    )
    PY

Each `runs/<run>/grounding/<slug>.md` is scoped by that agent's charter plus the
chart brief. If a grounding file says **Sparse grounding**, the agent must say so
in its reading and distinguish chart-grounded claims from corpus-grounded claims.

### 5. Spawn the nine structure agents as independent parallel subagents
For each of `ego`, `persona`, `shadow`, `anima-animus`, `parental`, `wound`,
`vocation`, `eros`, `numinous`, spawn a subagent (in parallel) whose context is
**only**:
- the charter at `agents/<slug>.md`, verbatim;
- the house rules at `agents/_house-rules.md`, verbatim — the anti-fabrication
  contract that binds every structure agent;
- the contents of `runs/<run>/chart-brief.md`;
- the contents of `runs/<run>/grounding/<slug>.md`;
- optional amplification material from `runs/<run>/grounding/amplification.md`
  when it speaks to that structure's key images;
- if blind: "Blind mode: you have no biography; do not invent one";
- if contextualized: the contents of `runs/<run>/biography.md`, explicitly named
  as biography supplied by the analyst;
- "Write your reading to `runs/<run>/structure/<slug>.md`."

Keep them independent — never let one agent see another's reading. Their tension
is the instrument (ADR-0003).

### 6. Run the depth-critic
Spawn one depth-critic subagent with `agents/_critic.md`, all nine structure
readings, the chart brief, and the grounding files. It attacks each reading for
vagueness, Barnum, cookbook flattening, and non-falsifiability — forcing
grounding in *this* chart and in cited depth-corpus material where available —
and writes its challenges to `runs/<run>/critic.md`. It writes no interpretation.

### 7. Run the interpreter
Spawn one interpreter subagent with `agents/_interpreter.md`, the nine structure
readings, **the critic's challenges (`critic.md`)**, and the chart brief. Building
on the threads the critic left standing, it writes the holistic portrait to
`runs/<run>/interpretation.md`.

### 8. Assemble + validate
    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart.run import assemble_dossier, validate_run
    run_dir = Path("runs/<native>-<ts>")
    assemble_dossier(run_dir)
    report = validate_run(run_dir)
    print("OK" if report.ok else report.problems)
    PY

If `validate_run` reports problems, fill the gap (provenance, chart brief, a
missing structure reading, critic section, portrait, or Reflection scaffold) and
re-assemble. When it is OK, present `runs/<run>/dossier.md`.

### 9. Compare two runs of the same native
To read two configurations side by side:

    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart.run import compare_runs
    path = compare_runs(Path("runs/<run-a>"), Path("runs/<run-b>"))
    print(path)
    PY

## Standing rules
- **Deterministic boundary (ADR-0002):** positions, houses, aspects, and
  configurations come from `compute_chart` only.
- **Multivalence (ADR-0001):** hold each archetype across its spectrum; never a
  single fixed meaning.
- **Anti-cookbook / anti-Barnum:** every claim must be specific to *this* chart
  and falsifiable against a living person. "Scorpio rising means intense" is
  failure.
- **Depth-corpus grounding:** cite retrieved material when it genuinely sharpens
  a claim; never pad a reading with generic quotations. If retrieval is sparse,
  say so plainly and continue from the chart brief.
- **Hermeneutic, not predictive:** the chart is a projective mandala of the
  psyche, read acausally — never a forecast.
