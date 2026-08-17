# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ARG APP_VERSION=latest
LABEL org.opencontainers.image.title="Immo-Boussole Orchestrator"
LABEL org.opencontainers.image.description="CLI & web orchestrator for Immo-Boussole instances"
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/Immo-Boussole/immo-boussole-orchestrator"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/        ./app/
COPY cli/        ./cli/
COPY templates/  ./templates/
COPY static/     ./static/

# Ensure instances.yaml exists (will be mounted as volume in production)
RUN echo "instances: []" > /app/instances.yaml

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false orchestrator \
    && chown -R orchestrator:orchestrator /app
USER orchestrator

# Expose web UI and MCP server ports
EXPOSE 9000 9001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/health')"

# Default: run the FastAPI web server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
