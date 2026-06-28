FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -r requirements-docker.txt

# Copy application source
COPY . .

# Environment
ENV FLASK_APP=wsgi:app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

EXPOSE 5000

# Entrypoint: init DB then start gunicorn
CMD ["sh", "-c", "flask init-db && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 --access-logfile - wsgi:app"]
