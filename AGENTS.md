# Orchestration Brief — Natal-Chart Depth Instrument

This is the brief the orchestrating Claude Code agent follows to perform one
**run**. The runtime is Claude Code itself (ADR-0007): you call deterministic
in-repo tools, spawn the structure agents as independent subagents, run the
interpreter, and assemble the dossier. You never compute chart positions yourself
(ADR-0002), and you never collapse an archetype to a single meaning (multivalence,
ADR-0001).

**Scope of this slice (#4):** natal layer only, **blind** mode, the four spine
structure agents (Ego, Persona, Shadow, Anima/Animus), no depth-critic, no corpus
retrieval. Agents reason from the chart brief + their charter. Grounding (RAG) and
the critic arrive in later slices.

## A run, end to end

### 1. Inputs
- `BirthData` (date, time, place).
- **Selection** — for this slice, `["natal"]`.
- **Run mode** — for this slice, `blind`: you are given **no** biography and must
  not invent one (Barnum-resistance, ADR-0004).
- A short `native` slug (e.g. `ada-lovelace`) for the run directory.

### 2. Compute the chart + scaffold the run — deterministic, never by hand
Generate a timestamp (`date -u +%Y-%m-%dT%H:%M:%SZ`) and revision
(`git rev-parse --short HEAD`), then:

    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart import BirthData, compute_chart
    from natal_chart.run import RunSpec, init_run
    brief = compute_chart(BirthData(date="1815-12-10", time="12:00", place="London, GB"))
    spec = RunSpec(
        native="ada-lovelace",
        structures=["ego", "persona", "shadow", "anima-animus"],
        models={"structure": "sonnet", "interpreter": "opus"},
    )
    run_dir = init_run(spec, brief, runs_root=Path("runs"),
                       timestamp="<TIMESTAMP>", revision="<REVISION>")
    print(run_dir)
    PY

This writes `runs/<native>-<ts>/` with `provenance.json`, `chart-brief.json`,
`chart-brief.md`, and an empty `structure/`.

### 3. Read the ground truth
Read `runs/<run>/chart-brief.md`. This — and only this — is the chart. Every agent
reads it; nobody recomputes it.

### 4. Spawn the four structure agents as independent parallel subagents
For each of `ego`, `persona`, `shadow`, `anima-animus`, spawn a subagent (in
parallel) whose context is **only**:
- the charter at `agents/<slug>.md`, verbatim;
- the contents of `runs/<run>/chart-brief.md`;
- "Blind mode: you have no biography; do not invent one";
- "Write your reading to `runs/<run>/structure/<slug>.md`."

Keep them independent — never let one agent see another's reading. Their tension
is the instrument (ADR-0003).

### 5. Run the interpreter
Spawn one interpreter subagent with `agents/_interpreter.md`, the four structure
readings, and the chart brief. It writes the holistic portrait to
`runs/<run>/interpretation.md`.

### 6. Assemble + validate
    uv run python - <<'PY'
    from pathlib import Path
    from natal_chart.run import assemble_dossier, validate_run
    run_dir = Path("runs/<native>-<ts>")
    assemble_dossier(run_dir)
    report = validate_run(run_dir)
    print("OK" if report.ok else report.problems)
    PY

If `validate_run` reports problems, fill the gap (a missing reading or portrait)
and re-assemble. When it is OK, present `runs/<run>/dossier.md`.

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
