# natal-chart

Astrology read through Jung, run by a stack of LLM agents: one for each structure of the psyche, plus a critic that tears up anything that sounds like a horoscope. You give it birth data, it writes a long psychological reading of the chart and shows its work.

It's a research sandbox, not a product. If a sentence in the output could apply to anyone, that counts as a failure.

## What happens when you run it

```
birth data
  -> compute_chart    real ephemeris math; the LLM never does this part
  -> 9 agents         each reads the whole chart through one Jungian structure, in parallel
  -> a critic         goes after vague, Barnum, and cookbook claims
  -> an interpreter   stitches the survivors into one portrait
  -> a dossier        the reading, plus every agent's notes and the chart it worked from
```

The nine are Ego, Persona, Shadow, Anima/Animus, the parental complexes, the wound, vocation, Eros, and the numinous. They read the same chart and reach different conclusions, on purpose. The Shadow agent's take on your Moon is a different thing from the Persona agent's.

## The one hard rule

The model never computes the chart. Positions, houses, aspects, configurations: all from the Swiss Ephemeris, via `kerykeion`. LLMs fumble the math, and a wrong chart quietly poisons every reading built on it, so the boundary is strict. Code computes, the model interprets, and they don't swap jobs.

Everything else is just text you can edit. The orchestration is `AGENTS.md`; each agent is a charter file in `agents/`. There's nothing to compile: you open the repo in Claude Code, point it at `AGENTS.md`, and it runs. Tuning the method means editing prose.

## Quickstart

```
uv sync
uv run pytest

# a chart
uv run compute_chart --date 1990-01-01 --time 12:00 --place Moscow --country-code RU

# a reading: open in Claude Code, say "do a run following AGENTS.md", read runs/.../dossier.md
```

`compute_chart` prints what it computed: positions, cusps, aspects, configurations. Tropical and Placidus by default. Add `--include-optional-bodies` or the transit/progression/solar flags if you want them.

## The corpus is the good part

Without it, the agents reason from training memory. With it, they're grounded in real books: Jung, Greene, Tarnas, Neumann, Hillman, von Franz. Drop PDFs or EPUBs into `corpus/sources/`, build the index, and retrieval feeds each agent passages scoped to its charter.

```
uv run ingest_corpus
```

It runs offline and stays on your machine. The texts are under copyright and the index runs to tens of megabytes, so both are gitignored. That also means the corpus won't follow you into a fresh checkout, so point runs at a fixed copy:

```
export NATAL_CORPUS_INDEX=/abs/path/to/corpus/index
```

No corpus, no problem: the run still happens and says so plainly instead of pretending it had sources. (It used to pretend. That was a bug.)

## Where the reasoning lives

- `CONTEXT.md` is the glossary. Start here.
- `docs/adr/` has the seven design decisions and the case for each.
- `agents/` is the charters, one per agent, in plain prose.

## Status, honestly

The plumbing works and has tests. The readings are only as good as the charters, and those are first drafts. They get sharper by running real charts and cutting the agents that don't earn their place. Run it blind (birth data only) for the honest test of whether it found anything; run it contextualized (you hand it a biography) for a reading that lands harder and is easier to fool yourself with.
