FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (owned by root and read-only for the app user)
COPY . .

# The API runs as a dedicated unprivileged user. Its only writable location
# is the uploads directory. The uid/gid (10001) is fixed because the
# one-shot "uploads-permissions" service in the Compose files hands the
# uploads volume to exactly this id.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && mkdir -p /app/uploads \
    && chown app:app /app/uploads \
    && chmod 750 /app/uploads
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
