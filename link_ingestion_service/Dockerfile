FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

# Worker: external link APIs -> RabbitMQ (link.metric) -> timeseries_storage -> InfluxDB
CMD ["python", "main.py"]
