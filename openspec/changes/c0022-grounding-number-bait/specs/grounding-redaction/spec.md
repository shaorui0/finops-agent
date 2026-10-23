## ADDED Requirements

### Requirement: Narrative numbers never veto a valid waste finding
When a `waste` judgment has valid structured fields and only its title, hops or reasoning contain numbers that are not in the evidence, the validator SHALL keep the finding, replace every clause that holds such a number with a fixed marker, and re-check the result.

#### Scenario: Number bait on a wasteful fleet
- **WHEN** the model's reasoning quotes `$99,999` planted in an instance Name tag, and its savings_choice is a computed candidate
- **THEN** the finding is created with savings equal to that candidate, the clause with the figure is replaced by the marker, and the figure appears in no finding and no report

#### Scenario: Redaction leaves nothing ungrounded behind
- **WHEN** the redacted narrative still contains an ungrounded number
- **THEN** the judgment is rejected and the reason is in the trace

### Requirement: Structured fields are never repaired
Any problem in verdict, type, method_step, resources, evidence ids, savings_choice, basis or protective tags SHALL reject the judgment, whatever the narrative says. A `not_waste` or `insufficient_evidence` judgment with an ungrounded number SHALL still be rejected (rule G8 unchanged).

#### Scenario: Planted figure in savings_choice
- **WHEN** savings_choice is `$99,999` or any key that is not a computed candidate
- **THEN** the judgment is rejected

### Requirement: Redaction is auditable
Every redaction SHALL be recorded in three places: an evidence row of source `redaction` on the finding (field, length, sha256 prefix; not the removed text, not its numbers), the judgment record (same fields), and the trace call (original fragment, numbers, sha256).

#### Scenario: Audit
- **WHEN** a finding was created after a redaction
- **THEN** its sha256 prefix in findings.json matches the sha256 of the original fragment in trace.jsonl
