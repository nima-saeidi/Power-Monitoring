FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# نصب ابزارهای مورد نیاز برای کامپایل و ارتباط با شبکه
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب وابستگی‌ها
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

# کپی کل کدهای سرویس
COPY . .

# اجرای مستقیم Worker
CMD ["python", "main.py"]
