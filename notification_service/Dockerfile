FROM python:3.10-slim

# Overridable package index (e.g. a local mirror where pypi.org is unreachable)
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_DEFAULT_TIMEOUT=60

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

CMD ["python", "main.py"]
