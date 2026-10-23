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

The synthetic account (`testenv/world.yaml`) hides most of its waste behind multi-hop reasoning and includes traps; see [`testenv/README.md`](testenv/README.md).

## What it does (planned)

| Layer | Question |
|---|---|
| Attribution | Who owns this spend? Are the tags/owners present — and correct? |
| Idle waste | What is running with nobody using it? |
| Potential waste | What stays over-provisioned long-term (not just a tidal peak)? |
| Optimization | Rightsizing, then commitments (SP/RI) — in that order |

Every finding carries its evidence (resource, metric, window, formula). Numbers are computed by deterministic code; the LLM classifies, explains and plans. Read-only by default.

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
| `hooks/` | Project guardrails — `aws_readonly_guard.py` blocks non-read AWS CLI calls (registered in `.claude/settings.json`) |

## License

MIT — see [`LICENSE`](LICENSE).
