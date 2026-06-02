# syntax=docker/dockerfile:1
#
# Targets:
#   - runtime (default): image for users
#   - dev: adds developer tooling + installs ".[dev]" extras
#
# Build runtime (users):
#   docker build -t jira-issues-dashboard:latest .
#
# Build dev image (contributors):
#   docker build --target dev -t jira-issues-dashboard:dev .

FROM python:3.13.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_CACHE=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Create the mount point for secrets
RUN mkdir -p /app/.streamlit

# Non-root user (better for Kubernetes)
RUN useradd -m -u 10001 appuser

# Copy only what we need for install + runtime
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY README.rst /app/README.rst
COPY jira_app /app/jira_app
COPY run_dashboard.py /app/run_dashboard.py

# Runtime writable directory (Debug page writes /app/data)
RUN mkdir -p /app/data \
  && chown -R appuser:appuser /app/data

# Install runtime deps from the locked uv environment
RUN pip install --no-cache-dir uv==0.11.18 \
  && uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')" || exit 1


# ---- Dev target (optional) ----
FROM base AS dev

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Allow non-root builds to write egg-info during editable/dev installs
RUN chown -R appuser:appuser /app

USER appuser
# Installs developer extras from the locked uv environment
RUN uv sync --frozen --extra dev


# ---- Runtime target (default) ----
FROM base AS runtime

USER appuser
CMD ["streamlit", "run", "run_dashboard.py", "--server.address=0.0.0.0", "--server.port=8501"]
