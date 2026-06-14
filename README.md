# natal-chart

A research sandbox for reading a natal chart the way a Jungian analyst might: as a projective map of the psyche, not a prediction engine. You hand it birth data and it produces a long, structured archetypal reading along with the reasoning behind every claim. The thing being studied is the method. Can a small ensemble of LLM agents, each working a different angle, surface something true about a person that a single cookbook-style pass never would?

It is not a horoscope generator. There is no "you're a Scorpio, so you're intense." If a claim could be true of anyone, it counts as a failure, not a reading.

## What's unusual about it

The decisions below are written up properly in `docs/adr/`. The short version.

### Code computes the chart, the model only interprets

Planetary positions, house cusps, aspects, and configurations come from the Swiss Ephemeris through `kerykeion`. Language models are unreliable at this arithmetic and hopeless at house math, and a wrong chart corrupts every interpretation built on top of it without anyone noticing. So the line is firm: the deterministic tool computes the chart, and the model is handed the result and never recomputes it.

### It reads by structure of the psyche, not by planet

Most astrology software walks a chart placement by placement. This walks it through nine Jungian structures: Ego, Persona, Shadow, Anima/Animus, the parental complexes, the wound, vocation, Eros, and the numinous. Each one is a separate agent that reads the whole chart through a single question. The Shadow agent and the Persona agent look at the same Moon and say different things on purpose, and the disagreement between them is usually where the interesting material is.

### A critic argues with the readings before they're synthesized

Once the agents are done, a depth-critic goes after their output looking for vagueness, Barnum statements, cookbook delineation, and anything that could never be shown wrong. Whatever survives goes to an interpreter, which writes one holistic portrait and keeps the contradictions open rather than ironing them flat.

### The corpus is real books, and it stays on your machine

Each agent is grounded in passages retrieved from a private library of depth-psychology and archetypal-astrology texts (Jung, Greene, Tarnas, Neumann, Hillman, von Franz, and so on). Retrieval runs locally, the index is built from your own copies, and nothing is sent anywhere. The texts are mostly under copyright, so they never enter git either.

### The runtime is Claude Code itself

There is no orchestration binary to run. The method lives as prose in `AGENTS.md` and one charter file per agent, and Claude Code follows it: compute the chart, pull grounding, fan out the agents, run the critic, run the interpreter, write the dossier. Changing how the instrument works means editing text, which is the whole point, because the method is what's under study and it gets revised constantly.

## How a run goes

```
birth data + selected layers + blind/contextualized
  -> compute_chart       exact chart (tropical, Placidus); the model never touches this
  -> chart brief         the single source of truth every agent reads
  -> retrieve grounding  charter-scoped passages from the local corpus
  -> nine agents         each reads the whole chart through one structure, in parallel
  -> depth-critic        attacks vague / Barnum / cookbook / unfalsifiable claims
  -> interpreter         one holistic portrait, tensions left intact
  -> dossier             portrait, readings, critic notes, chart brief, your reflection
```

Each run writes to `runs/<native>-<timestamp>/` with a provenance record (the config, the models, the charter versions it used) so you can tell two runs apart months later. There is no score at the end, on purpose. You read the dossier and write down what landed and what was generic, and every run ships with a reflection scaffold for doing exactly that.

## Setup

You need [uv](https://github.com/astral-sh/uv) and Python 3.12 or newer.

```
uv sync
uv run pytest
```

## Computing a chart

```
uv run compute_chart --date 1990-01-01 --time 12:00 --place Moscow --country-code RU
```

That prints the chart brief: positions, house cusps, aspects, and any configurations it detects. Tropical zodiac and Placidus houses by default. Asteroids, Lilith, and the Part of Fortune are left out unless you pass `--include-optional-bodies`. You can add transits, progressions, solar arc, or a solar return with the matching date flags. Birth data never leaves the machine.

## The depth corpus

The corpus is the set of books that ground the readings. It sits in two gitignored directories:

```
corpus/sources/   your texts (PDF, EPUB, plain text)
corpus/index/     the built retrieval index (SQLite)
```

Put sources in and build the index:

```
uv run ingest_corpus
```

Ingestion keeps a record of what it indexed and what it skipped (the rule is depth and amplification sources, never cookbook delineation tables). The retrieval model is fit on your corpus and stored inside the index, so queries run offline with no downloads.

Since the corpus is gitignored, it won't travel into a fresh clone or a worktree. Point runs at a stable copy with an environment variable:

```
export NATAL_CORPUS_INDEX=/absolute/path/to/corpus/index
```

A run that can't find the index announces it instead of quietly grounding on nothing, which is a mistake that already cost me one bad reading.

## Running a reading

Open the repo in Claude Code and ask it to do a run following `AGENTS.md`. It handles the orchestration and leaves the result in `runs/.../dossier.md`. Run it blind (birth data only) when you want the honest test of whether the method finds anything, or contextualized (with a biography) when you want a reading that resonates but are willing to watch yourself for confirmation bias.

## Layout

```
CONTEXT.md          the glossary; start here for the vocabulary
AGENTS.md           the orchestration brief (the method, in prose)
docs/adr/           the seven decisions that shaped the design, and why
agents/             a charter per structure agent, plus the critic and interpreter
src/natal_chart/    chart computation, corpus ingestion, retrieval, run lifecycle
tests/
```

## Where it stands

A sandbox, not a product. The pipeline is complete and tested, retrieval is local and semantic, and a run goes end to end. What it lacks is mileage. The charters are first drafts and will only sharpen by running real charts and watching which agents earn their keep. If a design choice looks odd, the ADR that made it explains the reasoning.
