#!/usr/bin/env bash
# One-shot setup + run for the demo.
# Usage:  ./run.sh
set -euo pipefail

cd "$(dirname "$0")"

# venv
if [ ! -d .venv ]; then
  echo "→ creating venv…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip sentinel-oversight

# api key — must be set in the environment before running
: "${SENTINEL_API_KEY:?Set SENTINEL_API_KEY before running}"

clear
echo
echo "════════════════════════════════════════════════════════"
echo "  Sentinel demo — wire transfer with human approval"
echo "════════════════════════════════════════════════════════"
echo
python demo.py
