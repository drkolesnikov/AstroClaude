# Deterministic chart computation; the LLM never computes

Birth data is converted to an exact chart — planetary longitudes, house cusps,
aspects — by the **Swiss Ephemeris**, computed *locally* via a wrapper (e.g.
kerykeion or immanuel), and the LLM only ever interprets that structured chart.
The LLM never performs the astronomy. We chose this because LLMs compute
celestial positions unreliably — a wrong mandala would silently poison every
downstream archetypal hypothesis and destroy run-to-run reproducibility — and
because local computation keeps identifying birth data (confidential for an
analysand) off third-party services.

## Considered options

- **Raw pyswisseph** — more control, more code to own; still viable as the wrapper choice.
- **External astrology API** — less code, but leaks birth data and adds network/cost.
- **LLM-computed charts** — rejected outright: unreliable, non-reproducible.

## Consequences

Swiss Ephemeris (AGPL) becomes a foundational dependency. The exact wrapper
library is left open and will be confirmed at build time; the *boundary* — code
computes, LLM interprets — is the durable decision.
