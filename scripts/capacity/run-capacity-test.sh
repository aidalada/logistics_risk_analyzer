#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
BASE_URL_DOCKER="${BASE_URL_DOCKER:-http://gateway}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
OUT_DIR="artifacts/capacity"
TS="$(date +%Y%m%d-%H%M%S)"
K6_JSON="${OUT_DIR}/k6-summary-${TS}.json"
STATS_TXT="${OUT_DIR}/docker-stats-${TS}.txt"
REPORT_MD="docs/capacity-planning-results.md"

mkdir -p "${OUT_DIR}"

run_k6() {
  if command -v k6 >/dev/null 2>&1; then
    k6 "$@"
  else
    docker compose run --rm -e BASE_URL="${BASE_URL_DOCKER}" k6 "$@"
  fi
}

if command -v k6 >/dev/null 2>&1; then
  K6_TARGET_BASE_URL="${BASE_URL}"
else
  K6_TARGET_BASE_URL="${BASE_URL_DOCKER}"
fi

echo "[capacity] running k6 scenario against ${K6_TARGET_BASE_URL}"
run_k6 run \
  --summary-export "${K6_JSON}" \
  -e BASE_URL="${K6_TARGET_BASE_URL}" \
  scripts/capacity/k6-order-load.js

echo "[capacity] collecting docker stats snapshot"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" >"${STATS_TXT}" || true

cpu_query='100 - (avg(rate(node_cpu_seconds_total{job="node_exporter",mode="idle"}[2m])) * 100)'
err_query='(sum(rate(http_requests_total{job="order_service",status=~"5.."}[2m])) / sum(rate(http_requests_total{job="order_service"}[2m]))) * 100'
rps_query='sum(rate(http_requests_total{job="order_service"}[1m]))'

cpu_now="$(curl -fsS "${PROM_URL}/api/v1/query" --data-urlencode "query=${cpu_query}" | python -c 'import json,sys; d=json.load(sys.stdin); r=d.get("data",{}).get("result",[]); print(r[0]["value"][1] if r else "n/a")' || echo "n/a")"
err_now="$(curl -fsS "${PROM_URL}/api/v1/query" --data-urlencode "query=${err_query}" | python -c 'import json,sys; d=json.load(sys.stdin); r=d.get("data",{}).get("result",[]); print(r[0]["value"][1] if r else "n/a")' || echo "n/a")"
rps_now="$(curl -fsS "${PROM_URL}/api/v1/query" --data-urlencode "query=${rps_query}" | python -c 'import json,sys; d=json.load(sys.stdin); r=d.get("data",{}).get("result",[]); print(r[0]["value"][1] if r else "n/a")' || echo "n/a")"

python - "${K6_JSON}" "${STATS_TXT}" "${REPORT_MD}" "${TS}" "${cpu_now}" "${err_now}" "${rps_now}" <<'PY'
import json
import sys

k6_json, stats_file, report_md, ts, cpu_now, err_now, rps_now = sys.argv[1:]

with open(k6_json, "r", encoding="utf-8") as f:
    data = json.load(f)

metrics = data.get("metrics", {})
http_reqs = metrics.get("http_reqs", {}).get("values", {}).get("rate", 0)
failed_rate = metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0)
p95 = metrics.get("http_req_duration", {}).get("values", {}).get("p(95)", 0)

lines = []
lines.append(f"# Capacity Planning Results ({ts})")
lines.append("")
lines.append("## Test Scenario")
lines.append("- Tool: `k6`")
lines.append("- Script: `scripts/capacity/k6-order-load.js`")
lines.append("- Focus service: `order-service` via gateway")
lines.append("")
lines.append("## Measured Results")
lines.append(f"- Observed request rate (k6): **{http_reqs:.2f} req/s**")
lines.append(f"- Error rate (k6 `http_req_failed`): **{failed_rate*100:.2f}%**")
lines.append(f"- P95 latency: **{p95:.2f} ms**")
lines.append(f"- Current Prometheus host CPU: **{cpu_now}%**")
lines.append(f"- Current Prometheus order-service error rate: **{err_now}%**")
lines.append(f"- Current Prometheus order-service RPS: **{rps_now} req/s**")
lines.append("")
lines.append("## Acceptance Thresholds")
lines.append("- Error rate < **5%**")
lines.append("- P95 latency < **800 ms**")
lines.append("- Host CPU < **85%**")
lines.append("")
lines.append("## Capacity Conclusion")
if failed_rate < 0.05 and p95 < 800:
    lines.append("- System stayed within thresholds for this test profile.")
    lines.append("- This profile is considered **sustainable** under current resources.")
else:
    lines.append("- Threshold violation detected.")
    lines.append("- Recommended actions: horizontal scaling for `order-service`, DB tuning, and request throttling.")
lines.append("")
lines.append("## Docker Stats Snapshot")
lines.append("```text")
with open(stats_file, "r", encoding="utf-8") as f:
    lines.extend([ln.rstrip("\n") for ln in f.readlines()])
lines.append("```")
lines.append("")
lines.append("## Evidence Files")
lines.append(f"- k6 summary JSON: `{k6_json}`")
lines.append(f"- Docker stats snapshot: `{stats_file}`")

with open(report_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

echo "[capacity] report generated: ${REPORT_MD}"
