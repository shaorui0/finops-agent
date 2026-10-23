## ADDED Requirements

### Requirement: Plans on every run
Every run SHALL write `runs/<id>/plans.json` built through `finops_agent.remediate`, covering every finding (judged ones included) with savings above zero, plus commitment findings. Each plan SHALL carry `reversal_cost` and `rollback`, and the report SHALL show them and state that nothing was executed.

#### Scenario: Plans cover all savings
- **WHEN** a run finishes against the synthetic account
- **THEN** every finding with `monthly_savings_usd > 0` has a plan with `reversal_cost` in none/low/medium/high and a non-empty `rollback`, `skipped` is empty, and `report.html` contains "本次运行没有执行任何命令"

### Requirement: Five parts per finding
`finops_agent/fivepart.py` SHALL compute `status`, `spec`, `diff` for every finding from its type and its non-LLM evidence, `runbook` from the plan (or advice when there is no plan) and `prevention` from `finops_agent/prevention.py`. Field names SHALL equal `testenv.catalog.FIELDS`.

#### Scenario: Report cards
- **WHEN** `report.html` is parsed
- **THEN** the number of finding cards equals the number of findings and each card has exactly the five headings 现状, 期望, 差异, 处置, 预防, in that order

#### Scenario: Numbers from code
- **WHEN** a finding has savings above zero
- **THEN** its `diff` contains the formatted savings from the finding and none of its text is copied from `llm` evidence

### Requirement: Prevention table
`finops_agent/prevention.py` SHALL map every finding type to preventive controls and alert rule names; every alert name SHALL exist in `config/alerts/finops.rules.yml`.

#### Scenario: Alerts exist
- **WHEN** `python3 -m unittest finops_agent.test_fivepart` runs
- **THEN** every alert in the table is defined in the rules file and every detector and judge type has an entry

### Requirement: Owner on findings
Each finding SHALL carry `owner` from resource tags ("未知" when none), and its plan's `owner` SHALL equal it.

#### Scenario: Missing owner
- **WHEN** the stopped legacy instance has no owner tag
- **THEN** its finding and plan owner are "未知"
