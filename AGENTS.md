# Orchestration Brief — Natal-Chart Depth Instrument

This is the brief the orchestrating Claude Code agent follows to perform one
**run**. The runtime is Claude Code itself (ADR-0007): you call deterministic
in-repo tools, spawn the structure agents as independent subagents, run the
interpreter, and assemble the dossier. You never compute chart positions yourself
(ADR-0002), and you never collapse an archetype to a single meaning (multivalence,
ADR-0001).

**Current scope:** the four spine structure agents (Ego, Persona, Shadow,
Anima/Animus), whole-layer Selection, blind/contextualized run modes, run
provenance, a critic artifact section, Reflection, and side-by-side comparison.
The full nine-agent roster and retrieval-grounded critic arrive in later slices;
until then, agents reason from the chart brief + their charter, and the critic
section applies the standing anti-Barnum rules below.

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
        structures=["ego", "persona", "shadow", "anima-animus"],
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

### 4. Spawn the four structure agents as independent parallel subagents
For each of `ego`, `persona`, `shadow`, `anima-animus`, spawn a subagent (in
parallel) whose context is **only**:
- the charter at `agents/<slug>.md`, verbatim;
- the contents of `runs/<run>/chart-brief.md`;
- if blind: "Blind mode: you have no biography; do not invent one";
- if contextualized: the contents of `runs/<run>/biography.md`, explicitly named
  as biography supplied by the analyst;
- "Write your reading to `runs/<run>/structure/<slug>.md`."

Keep them independent — never let one agent see another's reading. Their tension
is the instrument (ADR-0003).

### 5. Write the critic section
Read the structure readings and chart brief, then write
`runs/<run>/critic.md`. Until the dedicated critic charter lands, use the
standing rules below as the critic's charter: attack vagueness, Barnum,
cookbook flattening, and non-falsifiability; demand chart-specific grounding.

### 6. Run the interpreter
Spawn one interpreter subagent with `agents/_interpreter.md`, the four structure
readings, the critic section, and the chart brief. It writes the holistic
portrait to `runs/<run>/interpretation.md`.

### 7. Assemble + validate
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

### 8. Compare two runs of the same native
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
- **Hermeneutic, not predictive:** the chart is a projective mandala of the
  psyche, read acausally — never a forecast.
