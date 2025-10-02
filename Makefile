.PHONY: test

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
