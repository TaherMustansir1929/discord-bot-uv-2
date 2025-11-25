# Multi-stage build for optimized Discord bot image
# Stage 1: Builder stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages
# Keep minimal - only what's needed for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official image (faster than pip install)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv (much faster than pip)
# --no-cache prevents caching, reducing image size
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install only runtime dependencies:
# - ffmpeg for audio/voice support (Discord music bot)
# - ca-certificates for HTTPS requests
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p audio db images/anime images/generated_images

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/usr/local/bin:$PATH"

# Run as non-root user for security
RUN useradd -m -u 1000 botuser && \
  chown -R botuser:botuser /app
USER botuser

# Health check (optional - adjust endpoint/command as needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command - runs main.py
CMD ["python", "main.py"]
