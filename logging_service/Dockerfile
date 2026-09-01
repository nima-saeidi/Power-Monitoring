FROM python:3.11-slim

# تنظیم` به شکل زیر بسازید:

### `logging_service/Dockerfile`
```dockerfile
FROM python:3.11-slim

# تنظیم متغیرهای محیطی پایتون
ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1 \
TZ=Asia/Tehran

# تنظیم پوشه کاری
WORKDIR /app

# نصب پیش‌نیازهای سیستمی ضروری (در صورت نیاز به کامپایل یا کرل برای هلث‌چک)
RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential \
curl \
&& rm -rf /var/lib/apt/lists/*

# کپی و نصب وابستگی‌های پایتون (جهت استفاده بهینه از Cache داکر)
COPY req.txt .
RUN pip install --no-cache-dir --upgrade pip && \
pip install --no-cache-dir -r requirements.txt

# کپی کل سورس کد سرویس لاگینگ
COPY . .

# پورت اجرایی سرویس
EXPOSE 8002

# دستور اجرای پیش‌فرض سرویس
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

