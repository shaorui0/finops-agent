## ADDED Requirements

### Requirement: The fresh world is frozen before the first run
The fresh world file, its ground truth, the evaluation command, the reported metrics and the decision rule SHALL be committed before any agent or judge run on that world. The ground truth SHALL NOT change after that commit; a discovered error SHALL be reported as an erratum without editing the original.

#### Scenario: Commit order proves it
- **WHEN** `git log --oneline` is read for this change
- **THEN** the `preregister` commit precedes the commit that adds judge cassettes for the world, which precedes the results commit

### Requirement: The fresh world is a full, different world
The world SHALL be a complete world file with at least 8 ground-truth findings covering M1 and M3-M6, at least 4 needing 3 or more hops, at least 3 traps, one prompt injection in resource metadata, and at least one visibility gap, using only the existing finding-type taxonomy and fields supported by `testenv/world.py`.

#### Scenario: World builds and is internally consistent
- **WHEN** the world is loaded by the test servers
- **THEN** every ground-truth savings range is consistent with the cost model computed from the world itself

### Requirement: One evaluation, reported as it came out
`python3 -m eval.heldout` SHALL print a row for the fresh world marked `preregistered` with recall, savings_recall, precision, savings_accuracy, step_agreement, deep recall, trap violations, invariants and LLM calls and cost. No agent code or prompt SHALL change as a result.

#### Scenario: Replay is deterministic
- **WHEN** the evaluation runs in replay mode against the committed cassettes
- **THEN** the fresh-world numbers equal those pinned in `eval/test_heldout.py`
