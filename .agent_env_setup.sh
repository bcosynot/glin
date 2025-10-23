#!/usr/bin/env bash
set -euo pipefail

# Use Python 3.13 as specified
PYTHON_VERSION=3.13
python3.13 -m venv .venv
source .venv/bin/activate

# Install uv if missing
if ! command -v uv &> /dev/null; then
  pip install uv
fi

uv sync --group dev
python --version
uv --version
