FROM python:3.11-slim

# جلوگیری از نوشتن فایل‌های .pyc و بافر کردن لاگ‌ها
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# نصب پکیج‌های سیستمی مورد نیاز (در صورت نیاز به کامپایل پکیج‌ها)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# کپی نیازمندی‌ها و نصب آن‌ها
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

# کپی کل کدهای سرویس
COPY . .

# اجرای ورکر به عنوان اسکریپت مستقل
CMD ["python", "main.py"]
