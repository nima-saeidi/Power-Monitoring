# استفاده از نسخه سبک پایتون ۳.۱۱ (یا نسخه مدنظر شما)
FROM python:3.11-slim

# جلوگیری از نوشتن فایل‌های .pyc و بافرینگ لاگ‌ها
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تنظیم پوشه کاری داخل کانتینر
WORKDIR /app

# نصب پیش‌نیازهای سیستمی برای پکیج‌هایی مثل asyncpg یا psycopg2
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن کل کدهای پروژه به داخل کانتینر
COPY migrations .

# باز کردن پورت ۸۰۰۰
EXPOSE 8000

# دستور اجرای برنامه (تضمین پشتیبانی از وب‌سوکت با پکیج websockets)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets"]
