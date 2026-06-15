# AstroClaude

This is a personal project that I initiated while fusing my fascination with a few things at once: the occult, archetypal astrology, the analytical psychology of Jung and post-Jungian schools.

The idea came to me from interacting with LLMs. These fascinating machines are very good at automating language (and, well, also happen to be good at code and that's all the buzz, but I don't really care about SWEs getting replaced or my humble mortal shell getting turned into a paperclip by ASI), and they sparked my curiosity about whether they can be made to automate something more interesting - the archetypal fields and the difficult task of archetypal readings of astrological charts.

A sophisticated reader and appreciator of the occult might rightfully claim that we already have an abundance of automated chart-reading tools, and they would be right.
However, the issue is that those tools don't quite capture the unified reading that can be performed by a proficient practitioner of the occult, and the task of finding a somewhat decent archetypal astrologer is quite Sisyphean even in the era of the Internet.

And that's where AstroClaude comes in.
An automated language machine with a bolted-on corpus of books, serving as a runtime for interpreting the chart.

It is by no means capable of replacing a decent reading (at least at the current date, Opus 4.6-4.8 tier models). Maybe Fable and consecutive improvements in the ML scene will make this tool more exciting to work with.
But, nevertheless, for someone already versed in the fine art of amplification and archetypal astrology, this can serve as a fun stick to chew on and maybe gather some interesting insights into the chart.

The text after this section was authored by Claude, and I don't claim to understand even half of the tech argot it emits, but maybe it'll be useful for your own agent to get a better read on how this machinery works.

Have fun readings!

## What happens when you run it

```
birth data
  -> compute_chart    real ephemeris math; the LLM never does this part
  -> 9 agents         each reads the whole chart through one Jungian structure, in parallel
  -> a guard          flags any aspect or station an agent named that the chart doesn't contain
  -> a critic         goes after vague, Barnum, and cookbook claims
  -> an interpreter   stitches the survivors into one portrait
  -> a dossier        the reading, plus every agent's notes and the chart it worked from
  -> an HTML report   the same dossier as a self-contained, multi-page site
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

# render that reading as a self-contained HTML report
uv run render_report runs/<native>-<timestamp>
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
- `docs/adr/` has the design decisions and the case for each.
- `agents/` is the charters, one per agent, in plain prose.

## Status, honestly

The plumbing works and has tests — the chart math, the guard that flags invented aspects, the corpus retrieval, the HTML rendering. The readings are only as good as the charters, and those are first drafts. They get sharper by running real charts and cutting the agents that don't earn their place. Run it blind (birth data only) for the honest test of whether it found anything; run it contextualized (you hand it a biography) for a reading that lands harder and is easier to fool yourself with.
