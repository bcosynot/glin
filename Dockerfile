# Runtime image for Glin MCP server (stdio transport by default)
# Referencing devcontainer.json: use Python 3.13 and uv for dependency management

FROM python:3.13-slim AS runtime

# Install curl and git (git may be used by tools and during installs)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (https://docs.astral.sh/uv/)
# The script installs uv into ~/.local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
ENV PATH="/root/.local/bin:${PATH}"

# Set work directory
WORKDIR /app

# Copy project metadata first (better layer caching)
COPY pyproject.toml uv.lock ./

# Sync dependencies (include dev group similar to devcontainer.json)
# Using --frozen when possible to respect the lock file, but falling back if not strictly frozen
RUN uv --version \
    && (uv sync --group dev --frozen || uv sync --group dev)

# Copy application source
COPY glin ./glin
COPY main.py ./main.py

# Default command: run MCP server over stdio (matches Makefile run-stdio)
CMD ["uv", "run", "python", "main.py"]
