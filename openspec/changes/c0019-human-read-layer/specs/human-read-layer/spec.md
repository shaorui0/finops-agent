## ADDED Requirements

### Requirement: Diagrams derived from the repository
The repository SHALL contain `architecture`, `dataflow`, `visibility-chain`, `method`, `rot-lifecycle` and `harness-layers` as mermaid sources and rendered SVGs under `docs/diagrams/`, each box naming a component that exists on main.

#### Scenario: Stale render
- **WHEN** a `.mmd` file changes without re-rendering
- **THEN** `tools/test_build_index.py` fails because the recorded sha256 in `docs/diagrams/README.md` no longer matches

### Requirement: Guided index page
`tools/build_index.py` SHALL generate `reports/index.html` as one self-contained file (inline CSS and SVG, no script, no external reference) containing the project description, a reading path, the six diagrams, a table of every OpenSpec change, the key evidence pages and the current metrics.

#### Scenario: New change added
- **WHEN** a directory is added under `openspec/changes/`
- **THEN** the test fails until `reports/index.html` is regenerated and lists it

#### Scenario: Link integrity
- **WHEN** the index is parsed
- **THEN** every `href` and `src` resolves to an existing file or in-page anchor
