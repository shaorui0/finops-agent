PY ?= python3
AWS_PORT ?= 4566
PROM_PORT ?= 9090
RUN ?= local

.PHONY: test check servers demo eval stop

test:            ## all unit and end-to-end tests
	$(PY) -W ignore -m unittest hooks/test_aws_readonly_guard.py
	$(PY) -m unittest discover -s tools -p 'test_*.py'
	$(PY) -W ignore -m unittest testenv.test_testenv finops_agent.test_pipeline eval.test_score

check:           ## rules layer + leak scan
	$(PY) tools/check_rules.py

servers:         ## start both test servers in the background
	$(PY) -m testenv.aws_server --port $(AWS_PORT) & echo $$! > .aws_server.pid
	$(PY) -m testenv.metrics_server --port $(PROM_PORT) & echo $$! > .metrics_server.pid
	@for i in 1 2 3 4 5 6 7 8 9 10; do curl -sf localhost:$(AWS_PORT)/health >/dev/null && curl -sf localhost:$(PROM_PORT)/-/healthy >/dev/null && exit 0; sleep 1; done; exit 1

demo: servers    ## run the agent against the synthetic account
	$(PY) -m finops_agent run --aws-endpoint http://127.0.0.1:$(AWS_PORT) --prom http://127.0.0.1:$(PROM_PORT) --run-id $(RUN)

eval: demo       ## score the run against ground truth; fails on trap/invariant violations or regression
	$(PY) -m eval.score runs/$(RUN)/findings.json; status=$$?; $(MAKE) stop; exit $$status

stop:
	-@kill `cat .aws_server.pid` `cat .metrics_server.pid` 2>/dev/null; rm -f .aws_server.pid .metrics_server.pid
