## ADDED Requirements

### Requirement: Replay is the default and never silent
The client SHALL default to replay mode, read `eval/cassettes/<sha256(model + "\n" + prompt)>.json`, never start a subprocess or open a network connection in replay, and raise an error when the cassette is missing.

#### Scenario: Missing cassette
- **WHEN** a prompt has no cassette in replay mode
- **THEN** the run fails with an error that names the key and how to re-record

### Requirement: Record saves everything needed to replay
In record mode the client SHALL call `claude -p --output-format json` without tools or project settings, and save the reply text, token usage, cost and duration with the prompt. An existing cassette SHALL be reused unless FINOPS_LLM_FORCE=1.

#### Scenario: Reuse
- **WHEN** record mode sees a prompt it has recorded before
- **THEN** it makes no call

### Requirement: CI replays
The CI workflow SHALL run `make eval` with FINOPS_LLM_MODE=replay.

#### Scenario: No key
- **WHEN** CI runs without an API key
- **THEN** the eval still scores the judged findings
