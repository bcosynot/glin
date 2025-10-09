.PHONY: test sync hooks lint format run-stdio run-http docker-build

# Docker image defaults (override with `make docker-build IMAGE=name TAG=ver`)
IMAGE ?= glin
TAG ?= latest

# Install project and dev dependencies using uv
sync:
	@uv --version >/dev/null 2>&1 || { echo "uv is required. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv sync --group dev

# Configure Git to use the repo-provided hooks and ensure executability
hooks:
	@git config core.hooksPath .githooks
	@chmod +x .githooks/pre-commit || true
	@echo "Git hooks installed."

# Format and lint using Ruff via uv
format:
	@uv --version >/dev/null 2>&1 || { echo "uv is required. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv run ruff format

lint:
	@uv --version >/dev/null 2>&1 || { echo "uv is required. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv run ruff check --fix

# Run the test suite. If uv is available, prefer running via uv to use project-managed deps.
test:
	@set -e; \
	if command -v uv >/dev/null 2>&1; then \
		echo "Using uv to run tests"; \
		uv run pytest; \
	else \
		echo "Running pytest from current environment"; \
		pytest; \
	fi

# Run the MCP server with stdio transport (default)
run-stdio:
	@uv --version >/dev/null 2>&1 || { echo "uv is required. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv run python main.py

# Run the MCP server with HTTP transport on port 8000
run-http:
	@uv --version >/dev/null 2>&1 || { echo "uv is required. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv run python main.py --transport http

# Build Docker image from the Dockerfile at repo root
# Usage:
#   make docker-build               # builds IMAGE:TAG (defaults glin:latest)
#   make docker-build IMAGE=glin TAG=dev
# This target requires Docker to be installed and available on PATH.
docker-build:
	@docker --version >/dev/null 2>&1 || { echo "Docker is required. Please install Docker Desktop/Engine."; exit 1; }
	docker build -t $(IMAGE):$(TAG) -f Dockerfile .
