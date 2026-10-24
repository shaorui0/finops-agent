## ADDED Requirements

### Requirement: Links resolve
Every relative markdown link and every backticked repository path in `README.md`, `CONTRIBUTING.md`, `docs/**/*.md`, `rules/**/*.md`, `testenv/README.md` and `eval/EXPERIMENTS.md` SHALL resolve to an existing file or directory (http links, pure anchors, `runs/` paths and paths containing `<` or `*` are ignored).

#### Scenario: New document
- **WHEN** `docs/NARRATIVE.md` links to a change evidence file
- **THEN** that file exists

### Requirement: Chinese headings
No markdown heading in those files SHALL be English prose: outside backticks, a heading with two or more ASCII words of two or more letters MUST contain a CJK character.

#### Scenario: Mixed heading
- **WHEN** a heading is `## 判断层与 LLM 调用`
- **THEN** it passes

### Requirement: Status matches reality
The coverage matrix in `docs/REQUIREMENTS.md` section 5 SHALL name the change that delivered each row and SHALL contain no 计划, 待建 or 待设计 in its status column; rows blocked on the maintainer are listed explicitly under the table.

#### Scenario: Matrix audit
- **WHEN** the status column is scanned
- **THEN** the count of those words is 0 and the two maintainer-blocked exceptions are listed

### Requirement: Honest results
`README.md` and `docs/NARRATIVE.md` SHALL report in-sample, contaminated held-out and preregistered results as separate tiers with numbers copied from `eval/EXPERIMENTS.md`.

#### Scenario: Tier table
- **WHEN** a reader opens README section 1.3
- **THEN** the preregistered row shows recall 0.75, savings recall 0.568, deep recall 0.667 and 1 trap violation
