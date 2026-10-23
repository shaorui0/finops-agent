PY ?= python3
AWS_PORT ?= 4566
PROM_PORT ?= 9090
RUN ?= local
# replay | record | live, see finops_agent/llm.py
export FINOPS_LLM_MODE ?= replay
PROM_URL ?= http://127.0.0.1:9090
AWS_ENDPOINT ?=

.PHONY: test check servers demo eval record stop alerts-test inspect rot-demo

test:            ## all unit and end-to-end tests
	$(PY) -W ignore -m unittest hooks/test_aws_readonly_guard.py
	$(PY) -m unittest discover -s tools -p 'test_*.py'
	$(PY) -W ignore -m unittest testenv.test_testenv testenv.test_catalog finops_agent.test_pipeline finops_agent.test_slo finops_agent.test_llm finops_agent.test_judge finops_agent.test_remediate finops_agent.test_fivepart eval.test_score

check:           ## rules layer + leak scan
	$(PY) tools/check_rules.py

servers:         ## start both test servers in the background
	$(PY) -m testenv.aws_server --port $(AWS_PORT) & echo $$! > .aws_server.pid
	$(PY) -m testenv.metrics_server --port $(PROM_PORT) & echo $$! > .metrics_server.pid
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -sf localhost:$(AWS_PORT)/health >/dev/null && curl -sf localhost:$(PROM_PORT)/-/healthy >/dev/null && exit 0; sleep 1; done; exit 1

demo: servers    ## run the agent against the synthetic account
	$(PY) -m finops_agent run --aws-endpoint http://127.0.0.1:$(AWS_PORT) --prom http://127.0.0.1:$(PROM_PORT) --run-id $(RUN) --no-state

eval: demo       ## score the run against ground truth; fails on trap/invariant violations or regression
	$(PY) -m eval.score runs/$(RUN)/findings.json; status=$$?; $(MAKE) stop; exit $$status

record:          ## re-record LLM cassettes with real `claude -p` calls (delete stale eval/cassettes/*.json first), then score
	FINOPS_LLM_MODE=record $(MAKE) eval

rot-demo:        ## three runs against base / next_month / month_after: shows resolved, regressed and new (own ports, own temp state)
	# no judge: the later-month worlds have no LLM cassettes (recording is a separate, deliberate act); rot is decided by deterministic detectors
	FINOPS_NO_JUDGE=1 bash scripts/rot_demo.sh

stop:
	-@kill `cat .aws_server.pid` `cat .metrics_server.pid` 2>/dev/null; rm -f .aws_server.pid .metrics_server.pid

PROMTOOL ?= docker run --rm -v $(CURDIR)/config/alerts:/w -w /w --entrypoint promtool prom/prometheus:v2.53.0

alerts-test:     ## validate and unit-test the FinOps alert rules
	$(PROMTOOL) check rules finops.rules.yml
	$(PROMTOOL) test rules finops.rules.test.yml

inspect:         ## one inspection run with cross-run state (what cron calls); exports runs/<id>/finops_metrics.prom
	$(PY) -m finops_agent run $(if $(AWS_ENDPOINT),--aws-endpoint $(AWS_ENDPOINT),) --prom $(PROM_URL) --run-id inspect-$$(date -u +%Y%m%dT%H%M%SZ)
