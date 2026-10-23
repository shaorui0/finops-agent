## ADDED Requirements

### Requirement: Proposal only, never apply
The sync tool SHALL only read the parent rules and this repo, and SHALL write nothing except the proposal file given by `--out`.

#### Scenario: Protected output
- **WHEN** `--out` points inside the parent rules directory or this repo's `rules/`
- **THEN** the tool refuses and writes nothing

### Requirement: Classify differences
The tool SHALL list changed mapped axioms as updates, new unmapped parent axioms as "candidate, needs human decision", and axioms whose 来源 says 项目原生 as "propose back to parent".

#### Scenario: New parent axiom
- **WHEN** a parent axiom file is absent from the manifest and not in the mapping table
- **THEN** it appears only under candidates and is not added to `rules/axioms/`

### Requirement: No private text in output
Parent files matching any leak pattern SHALL be flagged and none of their text SHALL appear in the proposal.

#### Scenario: Private pattern
- **WHEN** a changed parent file contains text matching `.leak_patterns.local`
- **THEN** the proposal names the file and the pattern index only
