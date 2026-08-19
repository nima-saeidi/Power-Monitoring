FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY main_api/req.txt ./req.txt

RUN pip install --no-cache-dir -r req.txt

COPY main_api ./main_api

ENV PYTHONPATH=/app

CMD ["uvicorn", "main_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
