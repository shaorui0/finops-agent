#!/usr/bin/env bash
# Savings verification end to end: three periods (base, next_month, month_after), one agent run each,
# Cost Explorer per period, then the generated document and HTML page.
# Ports 34566/34567 (the module starts and stops the servers itself, one pair per period).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}
OUT_MD=${OUT_MD:-docs/SAVINGS_VERIFICATION.md}
OUT_HTML=${OUT_HTML:-reports/savings-verification.html}
for port in 34566 34567; do
  if lsof -iTCP:$port -sTCP:LISTEN >/dev/null 2>&1; then echo "port $port is busy" >&2; exit 1; fi
done
$PY -m finops_agent.verify_savings --port-base 34566 --out-md "$OUT_MD" --out-html "$OUT_HTML"
echo "wrote $OUT_MD and $OUT_HTML"
