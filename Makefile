.PHONY: test sync hooks lint format run-stdio run-http

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
