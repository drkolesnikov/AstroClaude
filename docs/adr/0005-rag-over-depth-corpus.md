# Ground agents via RAG over a curated depth corpus — no cookbook tables

From v1, structure agents are grounded by retrieval over a curated **depth
corpus** — archetypal-astrological (Tarnas, Greene), Jungian-theoretical (Jung
CW, Hillman, Edinger, von Franz), and mythic-amplification sources — rather than
reasoning from model memory alone. Crucially, the corpus **excludes cookbook
delineation tables** ("X in Y means Z") — even though they are the most abundant
astrological text available — because mechanical delineation reintroduces exactly
the cookbook flattening the instrument exists to resist. Each agent retrieves
scoped to its charter; amplification draws mythic parallels to the chart's key
images.

## Considered options

- **Reasoning-first, corpus deferred** — rejected in favour of lineage fidelity now.
- **Cookbook RAG** — rejected outright (flattening).

## Consequences

- Adds a retrieval subsystem + embeddings/vector-store dependency from v1.
- The corpus is for *private research use*; source texts (largely in copyright)
  are not redistributed.
- Curation by the depth-not-cookbook rule is ongoing editorial work, not a
  one-time ingest.
