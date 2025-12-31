# Multi-stage Dockerfile for ML Model Serving
# Stage 1: Build dependencies
# Stage 2: Production runtime (smaller image)

# ============================================================================
# STAGE 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# STAGE 2: Production Runtime
# ============================================================================
FROM python:3.11-slim as production

# Labels for container metadata
LABEL maintainer="ML Team <ml-team@company.com>"
LABEL version="1.0"
LABEL description="ML Model Inference Server"

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ .

# Copy model artifacts (if baked into image)
# COPY models/ /app/models/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    MODEL_PATH=/app/models \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER appuser

# Run the application
# Using uvicorn with multiple workers for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]

# ============================================================================
# BUILD COMMANDS:
# ============================================================================
# Build:
#   docker build -t ml-model:v1 -f Dockerfile ..
#
# Run locally:
#   docker run -p 8080:8080 ml-model:v1
#
# Run with model volume:
#   docker run -p 8080:8080 -v /path/to/models:/app/models ml-model:v1
#
# Push to registry:
#   docker tag ml-model:v1 myregistry.azurecr.io/ml-model:v1
#   docker push myregistry.azurecr.io/ml-model:v1
# ============================================================================
