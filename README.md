# finops-agent

An AWS FinOps agent that finds cloud waste with evidence — and a worked example of building an LLM agent with specs, evals and guardrails.

> Status: M0 (skeleton). Requirements and roadmap: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md).

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
| `context/` | Distilled project context (axioms, rules) — planned |
| `hooks/` | Project guardrails — `aws_readonly_guard.py` blocks non-read AWS CLI calls (registered in `.claude/settings.json`) |

## License

MIT — see [`LICENSE`](LICENSE).
