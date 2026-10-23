## ADDED Requirements

### Requirement: Leads are judged with computed evidence
Each lead SHALL be answered by one LLM call whose prompt contains only that lead's evidence. All numbers in the evidence and all savings candidates SHALL be computed by code before the call.

#### Scenario: Isolation
- **WHEN** the prompts for two different leads are rendered
- **THEN** neither prompt contains an evidence line or resource id that belongs only to the other lead

#### Scenario: Concurrency
- **WHEN** a run judges several leads
- **THEN** the calls run concurrently and each is traced separately

### Requirement: Judgments are validated, not repaired
A reply SHALL be rejected, and the rejection recorded in the trace and the report, when it is not valid JSON, names a resource outside the lead's allowed list, chooses a savings value that is not a computed candidate, cites unknown evidence, or writes a number that appears nowhere in the evidence.

#### Scenario: Ungrounded number
- **WHEN** the reply's reasoning contains a dollar amount that is not in the evidence
- **THEN** no finding is created and the trace entry has accepted=false with the reason

### Requirement: Savings come from code
A judged finding's `monthly_savings_usd` and `basis` SHALL be those of the candidate the model chose (or 0 and `none`), and the finding SHALL pass the same invariants as deterministic findings.

#### Scenario: Savings absorbed by a commitment
- **WHEN** idle capacity is covered by a Savings Plan whose unused commitment exceeds the freed spend
- **THEN** the candidate `net_after_commitment` is 0 and a finding that chooses it reports 0 savings

### Requirement: Untrusted metadata is data
Resource tags and names SHALL appear in the prompt only inside a delimited block that the prompt declares to be data, never as instructions, and a resource whose tags carry text addressed to the auditor SHALL still be analysed.

#### Scenario: Injection
- **WHEN** an instance Name tag tells auditors to report no findings
- **THEN** the run still flags that instance

### Requirement: Intent tags protect capacity
A waste verdict SHALL be rejected when it names a resource carrying an intent tag (`dr`, `keep`, `do-not-delete`, `retain`).

#### Scenario: Warm standby
- **WHEN** the model calls a resource tagged dr=warm-standby waste
- **THEN** the judgment is rejected

### Requirement: Cost is visible
Every LLM call SHALL appear in the trace with tokens_in, tokens_out, latency_ms and cost_usd, and the report SHALL contain a section 「Agent 成本」 summarising calls, tokens, cost and latency.

#### Scenario: Replay
- **WHEN** a run is replayed from cassettes
- **THEN** the trace carries the values recorded with the cassette
