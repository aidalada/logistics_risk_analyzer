#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
BASE_URL_DOCKER="${BASE_URL_DOCKER:-http://gateway}"
OUT_DIR="artifacts/capacity"
TS="$(date +%Y%m%d-%H%M%S)"
BASELINE_JSON="${OUT_DIR}/k6-baseline-${TS}.json"
SCALED_JSON="${OUT_DIR}/k6-scaled-${TS}.json"
REPORT_MD="docs/scaling-proof-report.md"
ORDER_REPLICAS="${ORDER_REPLICAS:-3}"

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

echo "[scaling-proof] ensuring baseline stack (order-service=1)"
docker compose up -d order-service gateway

echo "[scaling-proof] running baseline load test"
run_k6 run \
  --summary-export "${BASELINE_JSON}" \
  -e BASE_URL="${K6_TARGET_BASE_URL}" \
  scripts/capacity/k6-order-load.js

echo "[scaling-proof] scaling order-service to ${ORDER_REPLICAS} replicas"
docker compose up -d --scale order-service="${ORDER_REPLICAS}" order-service gateway
sleep 10

echo "[scaling-proof] running scaled load test"
run_k6 run \
  --summary-export "${SCALED_JSON}" \
  -e BASE_URL="${K6_TARGET_BASE_URL}" \
  scripts/capacity/k6-order-load.js

python - "${BASELINE_JSON}" "${SCALED_JSON}" "${REPORT_MD}" "${ORDER_REPLICAS}" "${TS}" <<'PY'
import json
import sys

baseline_json, scaled_json, report_md, replicas, ts = sys.argv[1:]

def metric(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    m = data.get("metrics", {})
    return {
        "rps": float(m.get("http_reqs", {}).get("values", {}).get("rate", 0)),
        "err": float(m.get("http_req_failed", {}).get("values", {}).get("rate", 0)) * 100,
        "p95": float(m.get("http_req_duration", {}).get("values", {}).get("p(95)", 0)),
    }

b = metric(baseline_json)
s = metric(scaled_json)

def pct_change(new, old):
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100

rps_delta = pct_change(s["rps"], b["rps"])
p95_delta = pct_change(s["p95"], b["p95"])
err_delta = s["err"] - b["err"]

lines = [
    f"# Scaling Proof Report ({ts})",
    "",
    "## Setup",
    "- Baseline: `order-service=1` replica",
    f"- Scaled: `order-service={replicas}` replicas",
    "- Load generator: `k6` (`scripts/capacity/k6-order-load.js`)",
    "",
    "## Results",
    f"- Baseline RPS: **{b['rps']:.2f}**",
    f"- Scaled RPS: **{s['rps']:.2f}**",
    f"- RPS change: **{rps_delta:+.2f}%**",
    f"- Baseline p95: **{b['p95']:.2f} ms**",
    f"- Scaled p95: **{s['p95']:.2f} ms**",
    f"- p95 change: **{p95_delta:+.2f}%**",
    f"- Baseline error rate: **{b['err']:.2f}%**",
    f"- Scaled error rate: **{s['err']:.2f}%**",
    f"- Error-rate delta: **{err_delta:+.2f} pp**",
    "",
    "## Threshold Evaluation",
    "- Target thresholds:",
    "  - error rate < 5%",
    "  - p95 latency < 800ms",
]

baseline_ok = b["err"] < 5 and b["p95"] < 800
scaled_ok = s["err"] < 5 and s["p95"] < 800

lines.append(f"- Baseline status: **{'PASS' if baseline_ok else 'FAIL'}**")
lines.append(f"- Scaled status: **{'PASS' if scaled_ok else 'FAIL'}**")
lines.append("")
lines.append("## Conclusion")
if scaled_ok and (s["rps"] >= b["rps"] or s["p95"] <= b["p95"]):
    lines.append("- Horizontal scaling improved or maintained service behavior under load.")
    lines.append("- This provides practical proof that `order-service` is scale-out capable.")
else:
    lines.append("- Scaling did not improve all target indicators.")
    lines.append("- Further tuning is needed (DB bottleneck analysis, gateway tuning, app profiling).")

lines.append("")
lines.append("## Evidence Files")
lines.append(f"- Baseline summary: `{baseline_json}`")
lines.append(f"- Scaled summary: `{scaled_json}`")

with open(report_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

echo "[scaling-proof] report generated: ${REPORT_MD}"
