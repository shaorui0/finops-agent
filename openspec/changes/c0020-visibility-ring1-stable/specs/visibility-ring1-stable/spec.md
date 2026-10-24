## ADDED Requirements

### Requirement: Ring 1 states signals in words
The ring-1 deriver SHALL ask for each need as `signal`, `concept`, `terms` and `scope`, and SHALL NOT ask for, or accept, a metric `name`. Each `terms` list SHALL hold 3 to 12 plain lowercase words.

#### Scenario: Names are rejected
- **WHEN** a derived need carries `name`, or a term contains an underscore
- **THEN** validation reports it and `derive` fails

### Requirement: Ring 2 discovers candidate names by meaning
For a need without `name`, ring 2 SHALL derive the candidate metric names deterministically from the live server's catalogue (name and HELP text), require at least two matching terms of which at least one is not a generic unit word, and require the scope label. A need with no candidate SHALL produce a query that matches nothing, so ring 3 reports it missing.

#### Scenario: Neighbour metrics are not substituted
- **WHEN** a memory-utilisation need is discovered against a catalogue that has only a CPU-utilisation metric
- **THEN** there is no candidate

### Requirement: Reviewed path unchanged
For needs that carry `name`, `ring2` SHALL produce the same plan as before and `ring4` with default arguments SHALL produce the same gaps as before.

#### Scenario: Pipeline gaps identical
- **WHEN** the pipeline runs on the reviewed file before and after this change
- **THEN** the `gaps` in `visibility.json` are byte-identical

### Requirement: Ring 4 reports a mix
With `mix=True`, ring 4 SHALL judge each need and report an SLI as covered only if all needs are covered, missing only if all are missing, otherwise partial, together with the per-status counts.

#### Scenario: One missing need
- **WHEN** an SLI has one covered and one missing need
- **THEN** its status is partial and its mix is 1 covered, 0 partial, 1 missing

### Requirement: Stability is measured as a mean
`python3 -m eval.score_visibility --samples N` SHALL derive ring 1 N times, score each draw against the reviewed file, and report mean, min and max overlap. The draws SHALL be recorded as cassettes so the mean is reproducible in replay.

#### Scenario: Replay reproduces the mean
- **WHEN** the command runs in replay mode with N=5
- **THEN** it makes no LLM call and prints the same per-sample overlaps and mean as the recorded run
