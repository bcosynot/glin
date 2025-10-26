#!/usr/bin/env bash
set -euo pipefail

python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
if ! command -v uv &> /dev/null; then
    pip install uv
fi
uv sync --group dev

