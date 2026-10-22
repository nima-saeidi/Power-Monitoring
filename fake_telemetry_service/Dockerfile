FROM python:3.11-slim

# Overridable package index (e.g. a local mirror where pypi.org is unreachable)
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_DEFAULT_TIMEOUT=60

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

# Demo only: synthetic telemetry.metric events + InfluxDB backfill for feeders without a reachable device
CMD ["python", "main.py"]
