# Triage Labels

The skills speak in terms of five canonical triage roles. In this repo each role
maps 1:1 to a GitHub label of the same name.

| Canonical role     | Label in this repo | Meaning                                  |
| ------------------ | ------------------ | ---------------------------------------- |
| `needs-triage`     | `needs-triage`     | Maintainer needs to evaluate this issue  |
| `needs-info`       | `needs-info`       | Waiting on reporter for more information |
| `ready-for-agent`  | `ready-for-agent`  | Fully specified, ready for an AFK agent  |
| `ready-for-human`  | `ready-for-human`  | Requires human implementation            |
| `wontfix`          | `wontfix`          | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the
corresponding label string from this table.

## Lane labels (project-specific, orthogonal to triage state)

This repo runs two implementation lanes and routes each ready issue to a model
with a **lane label**. These are *not* triage-state labels — they sit alongside a
readiness label:

| Label            | Lane                                                            |
| ---------------- | -------------------------------------------------------------- |
| `model:opus`     | High verbal-intelligence / writing / judgement work (Claude)   |
| `model:gpt-5.5`  | Tech-precision / monotropic technical depth (GPT-5.5)          |

A fully-triaged implementation issue normally carries one readiness label **and**
one lane label (e.g. `ready-for-agent` + `model:opus`).
