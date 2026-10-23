#!/usr/bin/env bash
# Rot detection end to end: three agent runs share one state file, each against a later month of
# the synthetic account. Run 2 shows resolved + new, run 3 adds regressed (see
# openspec/changes/c0010-rot-scenario/design.md for why a regression needs a third period).
# Ports 16566/16990 so it never collides with `make servers`.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}
AWS_PORT=16566 PROM_PORT=16990
TMP=$(mktemp -d)
STATE=$TMP/state.json
PIDS=()
cleanup() { [ ${#PIDS[@]} -gt 0 ] && kill "${PIDS[@]}" 2>/dev/null || true; rm -rf "$TMP"; }
trap cleanup EXIT

# run <run-id> <world file or "base"> <start> <end>
run() {
  local id=$1 world=$2 start=$3 end=$4 args=()
  [ "$world" != base ] && args=(--world "$world")
  $PY -m testenv.aws_server --port $AWS_PORT ${args[@]+"${args[@]}"} 2>/dev/null & PIDS=($!)
  $PY -m testenv.metrics_server --port $PROM_PORT ${args[@]+"${args[@]}"} 2>/dev/null & PIDS+=($!)
  for _ in $(seq 1 30); do
    curl -sf localhost:$AWS_PORT/health >/dev/null && curl -sf localhost:$PROM_PORT/-/healthy >/dev/null && break
    sleep 0.5
  done
  $PY -m finops_agent run --aws-endpoint http://127.0.0.1:$AWS_PORT --prom http://127.0.0.1:$PROM_PORT \
    --start "$start" --end "$end" --run-id "$id" --state "$STATE" --out "$TMP/runs" >/dev/null 2>"$TMP/$id.err" \
    || { cat "$TMP/$id.err"; exit 1; }
  kill "${PIDS[@]}" 2>/dev/null || true; wait "${PIDS[@]}" 2>/dev/null || true; PIDS=()
}

show() {  # show <run-id> <label>
  $PY - "$TMP/runs/$1/slo.json" "$1" "$2" <<'PY'
import json, sys
slo = json.load(open(sys.argv[1]))
d = slo["diff"]
print(f"== {sys.argv[2]} ({sys.argv[3]}) ==")
print("   " + "  ".join(f"{k}={len(v)}" for k, v in d.items()))
for k in ("resolved", "regressed", "new"):
    for e in d[k]:
        extra = f"  (resolved in {e['resolved_in']})" if k == "regressed" else ""
        print(f"   {k:10s} {e['key']}{extra}")
PY
}

run rot-1 base                          2026-09-01 2026-10-01
run rot-2 testenv/scenarios/next_month.yaml   2026-10-01 2026-11-01
run rot-3 testenv/scenarios/month_after.yaml  2026-11-01 2026-12-01
show rot-1 "run 1, base world, period 2026-09"
show rot-2 "run 2, next_month, period 2026-10"
show rot-3 "run 3, month_after, period 2026-11"
