## ADDED Requirements

### Requirement: Persistent cost anomalies produce a lead
A usage type whose window median daily cost exceeds twice its P25 baseline over the preceding history (at least 30 days, baseline above zero, peak above $5/day) SHALL produce a `cost_growth` lead, unless an in-window jump lead for the same usage type exists. The lead's `since` SHALL be the first day in history or window above twice the baseline. Existing leads SHALL keep their id, signal, evidence and params.

#### Scenario: Anomaly began before the window
- **WHEN** the history is flat at $10/day for 65 days and then $60/day, and the window is $60/day
- **THEN** one lead exists with `since` equal to the day the cost rose

#### Scenario: Base world unchanged
- **WHEN** the agent runs on `testenv/world.yaml` in replay
- **THEN** the 7 leads and the 7 cassette keys equal those of the previous version

### Requirement: Resolved needs cost-side evidence
A finding that is not reported in a run SHALL be `resolved` only if every resource that was present when it was last detected is now absent from the inventory or changed (attributes, or daily cost down by more than 10%). Otherwise it SHALL be `not_redetected` and SHALL NOT enter the resolved record, so its later reappearance is `persisting`, not `regressed`.

#### Scenario: Missed detection
- **WHEN** a gp2 volume finding disappears while the volume is still gp2 and billing the same
- **THEN** the diff lists it under `not_redetected` and `resolved` is empty

#### Scenario: Real fix
- **WHEN** the volume was deleted, or changed to gp3, or its cost line fell
- **THEN** the diff lists it under `resolved`
