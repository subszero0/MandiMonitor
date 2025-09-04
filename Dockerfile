# ================================
# Multi-stage Dockerfile for Security
# ================================

# Build stage - for compiling dependencies
FROM python:3.12-slim AS builder

# Security: Create non-root user for build
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
COPY paapi5-python-sdk-example ./paapi5-python-sdk-example

# Install dependencies in virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ================================
# Runtime stage - minimal attack surface
# ================================

FROM python:3.12-slim AS runtime

# Security: Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    # Runtime dependencies only
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Security: Switch to non-root user
USER appuser

# Security: Create logs directory with proper permissions
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Security: Use exec form for proper signal handling
CMD ["python", "-m", "bot.main"]