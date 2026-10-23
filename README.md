# finops-agent

An AWS FinOps agent that finds cloud waste with evidence — and a worked example of building an LLM agent with specs, evals and guardrails.

Two parts. **Part 1** is FinOps: the domain model, and the model I use to optimize cost. **Part 2** is the agent: how it is designed, and the principles behind it. FinOps is the vehicle; Part 2 is the point.

```bash
pip install -r requirements.txt
make eval                    # fake AWS + fake Prometheus → agent run → score against ground truth
open runs/local/report.html
```

No AWS account needed. The synthetic account and the two test servers are described in [`testenv/README.md`](testenv/README.md).

---

## How I think about this agent

The questions I asked before writing code, and the answers that shaped it. Each traces to a numbered requirement in [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md).

| Question | How I answer it |
|---|---|
| **Why build it?** | To practise and show agent engineering: making an agent controllable, measurable and improvable on a real system. Cost is a good vehicle because every company has the problem, the data is structured, and wrong answers have a price. (R1, R15) |
| **Agent engineering vs agent development** | Development makes the model do the task. Engineering decides what it may touch, what it is told, how its output is checked, and how it gets better without regressing. Context sets the ceiling; the harness sets the floor. (R1, R6) |
| **Where is the model weak?** | It hallucinates numbers, obeys text it should only read, and drifts from the path you meant. So: numbers come from code, resource metadata is treated as untrusted input (there is an injection in the test account), and the method fixes the path. (R6) |
| **Judge or verify?** | The agent verifies; it does not pronounce. Every claim carries evidence, every amount a basis, and invariants reject answers that cannot be true, whoever produced them. (R7) |
| **What does "better" mean?** | A number against ground truth: recall, savings-weighted recall, precision, trap violations. The baseline only moves up, and CI enforces it. (R7) |
| **Why hard test data?** | An agent that only finds idle volumes is a script. Real waste sits where sources meet (cost × inventory × utilization × useful work), and real traps look like waste. The test account is built that way. (R2, R3) |
| **Start from what?** | From the goal. First the SLIs a cost decision needs, then the search for metrics. Missing metrics are a finding. (R17, R19) |
| **What happens after the cleanup?** | It decays. Cost health gets SLOs, a waste budget, alert rules and an inspection cadence, and every run diffs against the last one to catch regressions. (c0007) |
| **How far does it act?** | Read-only, enforced twice (hook, IAM). Remediation stays a plan; commitments, which are the hardest to undo, stay a human decision. (R4, R16) |
| **Process as deliverable** | Every change is a spec, staged commits, an acceptance run with evidence, an HTML report and raw notes, so the reasoning stays visible as well as the code. (R8, R9) |
| **What stays private** | No employer data, ever. Synthetic data and a personal read-only account only; a leak scan runs on every commit. (constraints, REQUIREMENTS §4) |

---

## Part 1 · FinOps

### 1.1 Domain model

Every cost line is **unit price × usage × duration**, attached (or not) to a **resource**, which is owned (or not) by a **service** and a **team**. Optimization moves one of the three factors; attribution decides who has to act.

| Concept | What it is | Where the agent reads it |
|---|---|---|
| Spend | Bill lines by service, usage type, resource, tag; unblended vs amortized | Cost Explorer |
| Resource | Instances, volumes, snapshots, images, IPs, NAT gateways, launch templates, ASGs | EC2 / Auto Scaling APIs |
| Ownership | `owner` / `service` / `env` tags, and the facts that can contradict them (launch template, ASG, metric labels) | Tags + inventory + metrics |
| Pricing model | On-demand, Savings Plans / RIs (with utilization), list prices | Cost Explorer, Savings Plans API |
| Usage signal | Utilization (CPU, network), and **useful work** (jobs succeeded, requests served) | Prometheus |
| Constraint | The SLO a piece of capacity protects (latency headroom, DR standby) | Metrics + tags |
| Shared cost | Lines with no resource: NAT processing, cross-AZ transfer, commitment fees | Cost Explorer usage types |

Waste comes in shapes that need different evidence:

| Shape | Example | Minimum evidence |
|---|---|---|
| Idle | Unattached volume, unassociated IP | Inventory state |
| Stranded | Volume of an instance stopped for months; snapshots of deleted volumes | Inventory join + cost |
| Busy but useless | Fleet at 60% CPU whose jobs all fail | Cost + utilization + **work outcome** metrics |
| Path cost | NAT bytes multiplied by retries; chatty services across AZs | Usage-type cost + topology + traffic metrics |
| Stranded commitment | Savings Plan for a family the fleet migrated away from | Utilization history + inventory |
| Misattribution | Host tagged to one team, running another team's job | Tags vs launch template vs metric labels |
| **Not waste** | Tidal fleet with low average and real peaks; warm DR standby | Peak distribution, SLO, intent tags |

### 1.2 How I optimize cost

Full method: [`docs/METHOD.md`](docs/METHOD.md).

**Two tiers.** Operational optimization changes unit price (delete, downsize, change storage class, buy commitments); its ceiling is the discount rate. Architectural optimization changes usage or duration (scale to zero, run batch as ephemeral jobs, change the data path); its ceiling is an order of magnitude. Both are in every bill; the architectural ones hide deeper.

**Seven steps, in order.** M0 set cost goals and their SLIs before looking at data → M1 attribution → M2 80/20 ranking and surprises → M3 delete → M4 downsize / schedule → M5 commitments → M6 architecture. Delete before downsize before commit: buying commitment first locks waste in.

**Hard rules.**

- Headroom answers to an SLO. "70%" is a number; ask which SLO it protects before cutting it.
- A tide is not waste. Peaks that scale down are elasticity; capacity that never comes down is waste.
- Commitments rewrite savings. Stopping usage covered by an under-used plan saves nothing.
- One root cause can raise several bill lines. Find it before pricing each line.
- Savings never exceed spend. If they do, attribution is wrong.
- Every amount states its basis: billed, list price, or inferred.
- A cleanup decays. Cost health needs SLOs, a waste budget, alerts and an inspection cadence, the same as reliability. See [`docs/FINOPS_SLO.md`](docs/FINOPS_SLO.md).

### 1.3 Current results on the test account

| Metric | Value |
|---|---|
| Ground-truth findings recalled | 7 / 12 (all 3 shallow, 4 of 9 deep) |
| Savings-weighted recall | 19% |
| Precision · savings in range · method-step agreement | 100% · 100% · 100% |
| Trap violations · invariant violations | 0 · 0 |

The deterministic layer stops where cross-source judgment starts; those five findings are currently emitted as leads.

---

## Part 2 · The agent

### 2.1 Design

```
           ┌──────────── rules/ (soul, user, method, axioms) loaded every session ────────────┐
 AWS ──┐   │                                                                                   │
       ├─► collect (read-only, every call traced) ─► frozen snapshot ─► deterministic detectors ─┼─► findings ─┐
 Prom ─┘          ▲                                     │                    │                   │            ├─► invariants ─► report (by method step)
                  │                                     │                    └─► leads ─► judgment layer (LLM, next) ┘
                  │                                     └─► visibility chain: ① needs → ② plan → ③ search → ④ gaps
   hook + IAM: writes impossible                                                                 │
                                                                    eval vs ground truth + traps ┴─► CI gate
```

| Layer | Responsibility | Why it is separate |
|---|---|---|
| Collect | Pull inventory, cost, metrics; trace every call | The only layer that touches the outside world; read-only by construction |
| Snapshot | Freeze inputs | Runs replay exactly; a wrong answer can be reproduced |
| Detectors | Arithmetic and joins, one per method step | Every number recomputable; no model in the loop |
| Leads | Signals that need cross-source judgment, with open questions | The model gets questions and evidence, not raw dumps |
| Judgment (next) | Answer leads, classify, explain, plan | Where an LLM adds value, and where it is evaluated |
| Invariants | Savings ≤ spend, basis required, evidence required | Catches wrong answers whoever produced them |
| Visibility chain | Goal-first metric requirements → plan → search → gaps | Missing metrics are findings too |
| Eval | Score against ground truth; traps; regression baseline | "Better" is a number, and CI enforces it |
| SLO & rot | SLIs per run, waste budget, new / persisting / resolved / regressed across runs, Prometheus export + alert rules | A cleanup decays; the next run must notice |

### 2.2 Design principles

Each principle is a project axiom with a concrete enforcement point ([`rules/axioms/`](rules/axioms/INDEX.md)).

| Principle | Enforced by |
|---|---|
| Verifiable before correct | Evidence on every finding; ground-truth eval |
| Isolate → process → verify | Read-only collection, frozen snapshot, dry-run plans only |
| Data over opinion | Detectors compute; the model never does arithmetic |
| Errors cascade | `savings ≤ spend` invariant; amounts carry their basis |
| The agent is an unreliable component; SRE is its shell | Hook, server-side write rejection, IAM, eval gate |
| Responsibility is not delegated | Writes need a human; reports separate fact from inference |
| Start from the end | Visibility chain ring ① before any metric lookup |
| Context isolation | Leads carry exactly the evidence a judgment needs |
| Docs are memory | Rules layer, OpenSpec changes, notes per change |

### 2.3 How it is built

| Practice | Where |
|---|---|
| Spec-driven changes, committed in stages (proposal → spec → impl → docs → acceptance) | [`openspec/changes/`](openspec/changes/), `git log` |
| Acceptance per change: evidence, HTML report, raw notes; CI runs check → test → eval | [`reports/`](reports/), [`notes/blog/`](notes/blog/), [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| Guardrails in two layers | [`hooks/`](hooks/), [`docs/aws_account_hardening.md`](docs/aws_account_hardening.md) |
| Rules distilled from a private workspace | [`docs/DISTILLATION.md`](docs/DISTILLATION.md) |
| Coverage of harness practices, done and not done | [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) §5 |

### 2.4 Progress

One row per change, appended at acceptance. Full trail: `git log`, `openspec/changes/<id>/`.

| Change | Date | What | Takeaway | Report · Notes |
|---|---|---|---|---|
| 0000-init | 10-23 | Repo skeleton, requirements, change-loop skill | Interview on one thing: one project proves both the domain (FinOps) and agent engineering | [report](reports/0000-requirements.html) · [notes](notes/blog/0000-init.md) |
| c0001-requirements-v2 | 10-23 | Requirements v2 + read-only AWS hook | Guardrails before the first line of business code: write down what it must not do | [report](reports/0001-requirements-v2.html) · [notes](notes/blog/0001-requirements-v2.md) |
| c0002-visibility-chain | 10-23 | Coverage matrix + visibility chain | Start from the SLI the cost goal needs, then look for metrics — not the other way round | [report](reports/0002-visibility-chain.html) · [notes](notes/blog/0002-visibility-chain.md) |
| c0003-project-rules | 10-23 | Project rules layer, distilled from a private workspace | Distilling is deleting: 11 of 50 axioms kept, each with how it lands here | [report](reports/0003-project-rules.html) · [notes](notes/blog/0003-project-rules.md) |
| c0004-test-env | 10-24 | Synthetic account + fake AWS / Prometheus servers | Test data is hard because of where waste hides, not scale: idle-only detectors find < $100 of $8.7K/mo | [report](reports/0004-test-env.html) · [notes](notes/blog/0004-test-env.md) |
| c0005-pipeline-skeleton | 10-24 | collect → snapshot → detectors → visibility chain → report | Deterministic layer hits 7/12; the other 5 need cross-source judgment and are handed over as Leads | [report](reports/0005-pipeline-skeleton.html) · [notes](notes/blog/0005-pipeline-skeleton.md) |
| c0006-eval-ci | 10-24 | Scorer vs ground truth, regression baseline, Makefile, GitHub Actions; README in two parts | The first bugs the eval caught were in the scorer: a loose match inflated recall by 8 points | [report](reports/0006-eval-ci.html) · [notes](notes/blog/0006-eval-ci.md) |
| c0007-finops-slo | — | FinOps SLOs, alert rules, rot detection across runs, inspection cadence | *in progress* | |

### 2.5 Repo layout

| Path | Purpose |
|---|---|
| `finops_agent/` | The pipeline: collect → snapshot → detectors → visibility chain → report |
| `testenv/` | Synthetic account + test-aws-server + test-metrics-server |
| `eval/` | Scorer against ground truth + regression baseline |
| `config/` | Visibility requirements (ring 1), FinOps SLOs, alert rules (`config/alerts/`) |
| `ops/` | Inspection cadence (`crontab.example`) |
| `docs/` | Requirements, method, distillation, AWS hardening |
| `rules/` | Project rules layer |
| `hooks/` | Guardrails (registered in `.claude/settings.json`) |
| `openspec/` | Specs and change history |
| `.claude/skills/` | Project skills (`finops-change-loop` + OpenSpec skills) |
| `reports/`, `notes/blog/` | Per-change HTML reports and raw notes |
| `tools/` | Repo self-checks (`check_rules.py`: rules integrity + leak scan) |

## License

MIT — see [`LICENSE`](LICENSE).
