#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

python main.py \
  --mode live \
  --symbols RELIANCE TCS INFY \
  --auth-code "${UPSTOX_AUTH_CODE:?Set UPSTOX_AUTH_CODE}" \
  --instrument-keys NSE_EQ-RELIANCE-EQ NSE_EQ-TCS-EQ NSE_EQ-INFY-EQ \
  --log-level INFO
