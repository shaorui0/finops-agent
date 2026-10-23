## ADDED Requirements

### Requirement: Rules layer mirrors the source structure
The repository SHALL contain `rules/SOUL.md`, `rules/USER.md`, `rules/COMMUNICATION.md`, `rules/WORKSPACE.md`, `rules/axioms/INDEX.md` and `rules/skills/INDEX.md`.

#### Scenario: Structure check
- **WHEN** `tools/check_rules.py` runs
- **THEN** it fails if any of these files is missing

### Requirement: Rules are loaded every session
`CLAUDE.md` and `AGENTS.md` at the repository root SHALL instruct the agent to read the rules layer before any other work, and every path they reference SHALL exist.

#### Scenario: Dangling reference
- **WHEN** `CLAUDE.md` references a path that does not exist
- **THEN** `tools/check_rules.py` fails and names the path

### Requirement: Every axiom is enforceable
Each project axiom SHALL state its principle, what it means for FinOps, how this repository enforces it, and where it was distilled from; every axiom file SHALL be listed in `rules/axioms/INDEX.md` and vice versa.

#### Scenario: Axiom missing a section
- **WHEN** an axiom file lacks the 「本仓库怎么落地」 section
- **THEN** `tools/check_rules.py` fails

### Requirement: Public-safe
The rules layer SHALL contain no employer names, internal service names, account numbers, private paths or personal life details.

#### Scenario: Leak scan
- **WHEN** `tools/check_rules.py` runs
- **THEN** it fails on any match of the leak patterns
