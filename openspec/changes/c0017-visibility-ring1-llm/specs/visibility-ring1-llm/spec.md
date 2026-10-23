## ADDED Requirements

### Requirement: Goal-first derivation
The ring-1 deriver SHALL build its prompt only from the goals file and a fixed schema description, and SHALL NOT include any metric name served by the metrics server or any name from `config/visibility_requirements.yaml`.

#### Scenario: Prompt hygiene
- **WHEN** the prompt is built from `config/cost_goals.yaml`
- **THEN** no metric name from the test metrics server and no literal fragment of the reviewed requirements appears in it, and the goals file itself contains none

### Requirement: Same schema as the reviewed ring 1
`python3 -m finops_agent.visibility_llm derive` SHALL write a YAML whose `slis` entries carry `id`, `decision` and `need: [{signal, name, scope}]`, with `scope` limited to `running_instances`, `nat_gateways` or `services:<list>`, and every `name` a valid regex.

#### Scenario: Usable by rings 2-4
- **WHEN** the derived file is loaded with `visibility.ring1` and passed to `ring2`
- **THEN** one plan step is produced per need

### Requirement: Replay by default
Derivation SHALL go through `finops_agent/llm.py`; in replay mode it SHALL need no network and SHALL be byte-identical to the recorded output.

#### Scenario: Deterministic
- **WHEN** `derive` runs twice in replay mode
- **THEN** both outputs are identical and no `claude` process is started

### Requirement: Scored against the reviewed ring 1
`eval/score_visibility.py` SHALL report recall of reviewed needs, precision of derived needs and a per-SLI table, using a documented matching rule (scope overlap and a shared real metric name).

#### Scenario: Self-score
- **WHEN** the reviewed file is scored against itself
- **THEN** recall and precision are both 1.0
