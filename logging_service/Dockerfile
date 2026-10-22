FROM python:3.11-slim

# Overridable package index (e.g. a local mirror where pypi.org is unreachable)
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_DEFAULT_TIMEOUT=60

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Tehran

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY req.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r req.txt

COPY . .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/docs || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
