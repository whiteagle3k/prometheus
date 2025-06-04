# Prometheus Aletheia Service - Multi-Frontend Container
# Supports API, Telegram, and Shell modes in single container

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --only=main

# Copy application code
COPY . .

# Create data directory for logs
RUN mkdir -p data/logs

# Create non-root user for security
RUN groupadd -r aletheia && useradd -r -g aletheia aletheia
RUN chown -R aletheia:aletheia /app
USER aletheia

# Expose API port
EXPOSE 8000

# Default to API mode, can be overridden
ENTRYPOINT ["python", "prometheus.py", "--mode"]
CMD ["api"]

# Health check for API mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Labels for container metadata
LABEL version="0.6.0"
LABEL description="Aletheia AI Service - Multi-Frontend Container"
LABEL maintainer="Prometheus Team"

# Environment variables documentation
ENV TELEGRAM_TOKEN=""
ENV OPENAI_API_KEY=""
ENV ANTHROPIC_API_KEY="" 