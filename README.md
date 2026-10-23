# finops-agent

An AWS FinOps agent that finds cloud waste with evidence — and a worked example of building an LLM agent with specs, evals and guardrails.

> Status: pipeline skeleton runs end to end against a synthetic account. Requirements and roadmap: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md). Method: [`docs/METHOD.md`](docs/METHOD.md).

## Quickstart (no AWS account needed)

```bash
pip install -r requirements.txt
python3 -m testenv.aws_server &        # fake AWS on :4566 (read-only)
python3 -m testenv.metrics_server &    # fake Prometheus on :9090
python3 -m finops_agent run --aws-endpoint http://127.0.0.1:4566 --prom http://127.0.0.1:9090
open runs/*/report.html
```

`make eval` runs the same thing and scores it against the account's ground truth (recall, savings-weighted recall, precision, trap violations, invariants); CI fails on any trap hit or regression below `eval/baseline.json`.

The synthetic account (`testenv/world.yaml`) hides most of its waste behind multi-hop reasoning and includes traps; see [`testenv/README.md`](testenv/README.md).

## What it does (planned)

| Layer | Question |
|---|---|
| Attribution | Who owns this spend? Are the tags/owners present — and correct? |
| Idle waste | What is running with nobody using it? |
| Potential waste | What stays over-provisioned long-term (not just a tidal peak)? |
| Optimization | Rightsizing, then commitments (SP/RI) — in that order |

Every finding carries its evidence (resource, metric, window, formula). Numbers are computed by deterministic code; the LLM classifies, explains and plans. Read-only by default.

## Progress

One row per change, appended at acceptance. Full trail: `git log`, `openspec/changes/<id>/`.

| Change | Date | What | Takeaway | Report · Notes |
|---|---|---|---|---|
| 0000-init | 10-23 | Repo skeleton, requirements, change-loop skill | Interview on one thing: one project proves both the domain (FinOps) and agent engineering | [report](reports/0000-requirements.html) · [notes](notes/blog/0000-init.md) |
| c0001-requirements-v2 | 10-23 | Requirements v2 + read-only AWS hook | Guardrails before the first line of business code: write down what it must not do | [report](reports/0001-requirements-v2.html) · [notes](notes/blog/0001-requirements-v2.md) |
| c0002-visibility-chain | 10-23 | Coverage matrix + visibility chain | Start from the SLI the cost goal needs, then look for metrics — not the other way round | [report](reports/0002-visibility-chain.html) · [notes](notes/blog/0002-visibility-chain.md) |
| c0003-project-rules | 10-23 | Project rules layer, distilled from a private workspace | Distilling is deleting: 11 of 50 axioms kept, each with how it lands here | [report](reports/0003-project-rules.html) · [notes](notes/blog/0003-project-rules.md) |
| c0004-test-env | 10-24 | Synthetic account + fake AWS / Prometheus servers | Test data is hard because of where waste hides, not scale: idle-only detectors find < $100 of $8.7K/mo | [report](reports/0004-test-env.html) · [notes](notes/blog/0004-test-env.md) |
| c0005-pipeline-skeleton | 10-24 | collect → snapshot → detectors → visibility chain → report | Deterministic layer hits 7/12; the other 5 need cross-source judgment and are handed over as Leads | [report](reports/0005-pipeline-skeleton.html) · [notes](notes/blog/0005-pipeline-skeleton.md) |
| c0006-eval-ci | — | Eval + CI | *in progress* | |

## Repo layout

| Path | Purpose |
|---|---|
| `docs/` | Requirements, design |
| `openspec/` | Specs and change history — every change is one OpenSpec change + one commit |
| `.claude/skills/` | Project skills (`finops-change-loop` + OpenSpec skills) |
| `reports/` | One HTML report per change |
| `notes/blog/` | Raw idea notes per change |
| `rules/` | Project rules layer loaded every session (soul, user, communication, workspace, axioms, skills) — see `docs/DISTILLATION.md` |
| `tools/` | Repo self-checks (`check_rules.py`: rules integrity + leak scan) |
| `finops_agent/` | The pipeline: collect → snapshot → detectors → visibility chain → report |
| `testenv/` | Synthetic account + test-aws-server + test-metrics-server |
| `config/` | Visibility requirements (ring 1) |
| `eval/` | Scorer against ground truth + regression baseline |
| `hooks/` | Project guardrails — `aws_readonly_guard.py` blocks non-read AWS CLI calls (registered in `.claude/settings.json`) |

## License

MIT — see [`LICENSE`](LICENSE).
