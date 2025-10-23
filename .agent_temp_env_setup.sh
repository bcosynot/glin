#!/usr/bin/env bash
set -euo pipefail

rm -rf .venv
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
    export PATH="$HOME/.local/bin:$PATH"
fi
uv sync --group dev --frozen || uv sync --group dev
uv pip list
echo "Environment setup complete. Activate with: source .venv/bin/activate"