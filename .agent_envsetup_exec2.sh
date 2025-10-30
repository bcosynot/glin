#!/usr/bin/env bash
set -euo pipefail

# Create isolated environment directory (if not present)
python3.13 -m venv .venv
source .venv/bin/activate

# Install uv inside the virtualenv (if not already)
pip install --upgrade pip
pip install uv

# Install all dependencies (main + dev/test)
uv sync --group dev
