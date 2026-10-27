#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5001}"
BASELINE_SECONDS="${BASELINE_SECONDS:-30}"
SPIKE_SECONDS="${SPIKE_SECONDS:-10}"
BASELINE_RPS="${BASELINE_RPS:-5}"
SPIKE_RPS="${SPIKE_RPS:-25}"

post_student() {
  local i="$1"
  local email="demo-${RANDOM}-${i}-$(date +%s)@example.com"
  curl -s -o /dev/null -X POST "${BASE_URL}/students" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Load Test ${i}\",\"email\":\"${email}\",\"course\":\"Demo\"}" || true
}

hit() {
  local i="$1"
  case $((i % 10)) in
    0)
      curl -s -o /dev/null "${BASE_URL}/students/999999" || true
      ;;
    1 | 2)
      post_student "$i"
      ;;
    *)
      curl -s -o /dev/null "${BASE_URL}/students" || true
      ;;
  esac
}

burst() {
  local requests="$1"
  local i
  for ((i = 1; i <= requests; i++)); do
    hit "$i"
  done
}

echo "=== BASELINE: ${BASELINE_SECONDS}s at ~${BASELINE_RPS} req/s ==="
for ((s = 0; s < BASELINE_SECONDS; s++)); do
  burst "$BASELINE_RPS"
  sleep 1
done

echo "=== SPIKE: ${SPIKE_SECONDS}s at ~${SPIKE_RPS} req/s ==="
for ((s = 0; s < SPIKE_SECONDS; s++)); do
  burst "$SPIKE_RPS"
  sleep 1
done

echo "=== DONE: ~$((BASELINE_SECONDS * BASELINE_RPS + SPIKE_SECONDS * SPIKE_RPS)) requests sent ==="
