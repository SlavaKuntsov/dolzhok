# Status transitions are free

An item's status can move from any status to any other, except into the status it is already in (which is an error, not silence). We deliberately did not build a state machine: with exactly two trusted users, a linear `NEW → ORDERED → RECEIVED` pipeline that forbids backtracking would fight real usage (a mistap, a reopened order) more than it would protect anything.

## Consequences

- The UI's "pipeline" ordering (`NEW`, `ORDERED`, `RECEIVED`) is presentational; `CANCELLED` sits outside it.
- Repeating the current status returns a domain error rather than being a no-op.
