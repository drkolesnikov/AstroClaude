# Natal Chart Analysis (Method Sandbox)

A research sandbox for studying how an ensemble of LLM agents can read a natal
chart as a *depth-instrument* — surfacing non-obvious, generative archetypal
hypotheses about the native, judged hermeneutically rather than by metrics.

## Language

### The native and the output

**Native**:
The person whose birth data the chart is cast for, and whose psyche the analysis
probes.
_Avoid_: client, subject, querent, patient, analysand

**Archetypal hypothesis**:
A provisional, multivalent interpretive claim about the native's psyche, offered
for the analyst to test against the living person — never a pronouncement or a
prediction. The unit of output the sandbox is judged on.
_Avoid_: reading, prediction, result, verdict, trait

### The symbolic field

**Natal chart**:
Treated here as a projective, synchronistic mandala of the native's psyche (Jung)
— an acausal map to be read, never a causal or predictive mechanism.
_Avoid_: horoscope, forecast

**Planetary archetype**:
The multivalent collective principle a planet signifies (Tarnas) — e.g. Saturn as
limit, structure, time, and mastery at once. Not a fixed trait or a causal force.
_Avoid_: planetary influence, sign trait, placement-meaning

**Complex**:
How a planetary archetype is personally constellated in *this* native's psyche —
its feeling-toned, biographical inflection (Jung/Greene). The archetype is
collective; the complex is the native's.
_Avoid_: issue, hangup

**Multivalence**:
The principle that every planetary archetype expresses across a spectrum (from
afflicted to sublimated, literal to symbolic) and must never be collapsed to a
single valence — the chief guard against cookbook flattening. It governs the
*exploration* (the structure agents and the depth-critic), which holds the full
spectrum open; the interpreter then commits to the valence live in *this* chart
(ADR-0009). A process rule, not a property the final reading must preserve.
_Avoid_: fixed meaning, definition

### Chart composition

**Layer**:
A deterministically-computed temporal/technical stratum of the chart — natal,
transits, secondary progressions, solar arc, or solar return. The unit a scope
selector switches on or off.
_Avoid_: technique, chart type

**Selection**:
The per-run specification of which layers (and, later, which finer factors) are
in frame — from a single layer up to the full temporal picture. The sandbox's
input knob, distinct from how agents decompose what they're given.
_Avoid_: filter, config, mode

### The ensemble

**Chart brief**:
The deterministic, structured textual rendering of the computed chart — every
selected layer's exact placements, aspects, and configurations — that every
agent reads as ground truth. The grounding artifact; not itself interpretive.
_Avoid_: prompt, context dump, chart data

**Structure agent**:
An agent that reads the *whole* chart through a single Jungian structure of the
psyche (Shadow, Persona, Anima/Animus, …). The sandbox's facet. Defined by a
structure of the psyche, never by a planet, house, or aspect.
_Avoid_: planet agent, factor agent, facet

**Interpreter**:
The single strong synthesis agent that, having absorbed the structure agents'
outputs and the depth-critic's challenges, *commits* to one prioritized reading of
the chart from the individuation / Self vantage — a centre named and owned, the
rest subordinated. The integrating totality, not a peer in the fan-out; it commits
where the agents explored (ADR-0009).
_Avoid_: aggregator, summarizer, reducer, merger, field-holder

**Depth-critic**:
The agent that attacks each structure agent's reading for vagueness, Barnum,
cookbook flattening, and non-falsifiability — forcing specificity and grounding
in *this* chart before the interpreter synthesizes. The pipeline's quality guard,
not a perspective of its own.
_Avoid_: reviewer, validator, editor

**Charter**:
The single interpretive question a structure agent asks of the whole chart —
what fixes its turf so that two agents reading the *same* placement produce
*different* readings (the mother-imago vs the soul-image vs the erotic appetite
of one Moon). Overlap of significators is multivalence made manifest, not
duplication to be removed.
_Avoid_: role, scope

Current structure-agent roster (the research variable, expected to evolve): Ego
(conscious standpoint), Persona, Shadow, Anima/Animus, Parental complexes, Wound
(Chiron), Vocation/telos, Eros/relating, Numinous/transpersonal — plus the Self
as the interpreter's vantage. Anima/Animus is read *fluidly* (the contrasexual
soul-image, independent of the native's sex or orientation); supplied gender
informs but never hard-assigns.

### Running the instrument

**Run mode**:
Whether a run reads from birth data alone (**blind** — the default; Barnum-
resistant; the honest test of archetypal yield) or also against the native's
known biography (**contextualized** — clinical resonance, higher confirmation
risk). A per-run knob.
_Avoid_: profile, persona, dossier

### Grounding

**Depth corpus**:
The curated retrieval corpus that grounds the agents — archetypal-astrological
(Tarnas, Greene), Jungian-theoretical (Jung CW, Hillman, Edinger, von Franz), and
mythic-amplification sources. Explicitly *excludes* cookbook delineation tables,
which would reinstate the flattening the instrument resists.
_Avoid_: knowledge base, library, cookbook

**Amplification**:
The Jungian technique of enriching a chart image by gathering parallels from
myth, religion, alchemy, and fairy tale — a primary use of the depth corpus,
distinct from astrological delineation.
_Avoid_: lookup, research

### Runs & evaluation

**Run**:
A single execution of the pipeline for a given native, selection, and run mode —
the sandbox's unit of work and of comparison.
_Avoid_: session, job, analysis

**Run artifact**:
The self-contained, layered Markdown output of a run — its config/provenance, the
chart brief, every structure reading, the depth-critic's challenges, and the
interpreter's portrait — persisted for reading and cross-run comparison.
Informally, the *dossier*; its HTML presentation is the *rendered dossier*.
_Avoid_: report, output

**Rendered dossier**:
The self-contained, multi-page HTML rendering of the run artifact — the
individuation portrait, the computed chart wheel, every structure reading, and the
depth-critic — produced deterministically from the persisted artifacts for reading
and sharing. A presentation of the dossier, not a second source of truth.
_Avoid_: webpage, export, HTML dump

**Provenance**:
The full config a run auto-records — selection, run mode, model, prompt + corpus
versions, seed — making any judgement reproducible and attributable.
_Avoid_: metadata, log

**Reflection**:
The analyst's freeform recorded judgement of a run artifact — what landed, what
was generic or Barnum, what surprised. The sandbox's evaluation signal;
deliberately qualitative, never a score.
_Avoid_: score, rating, review
