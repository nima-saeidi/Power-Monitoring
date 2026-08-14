# استفاده از تصویر پایه پایتون ۳.۱۱
FROM python:3.11-slim

# جلوگیری از نوشتن فایل‌های .pyc و بافر شدن خروجی‌ها در لاگ داکر
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تنظیم مسیر کاری داخل کانتینر
WORKDIR /app

# کپی کردن فایل نیازمندی‌ها
# پیشنهاد می‌شود یک فایل req.txt مخصوص همین سرویس در پوشه telemetry_service بسازید
COPY req.txt .

# نصب کتابخانه‌ها
RUN pip install --no-cache-dir -r req.txt

# کپی کردن کل کدهای پوشه تله‌متری به داخل کانتینر
COPY . .

# اکسپوز کردن پورت ۸۰۰۱
EXPOSE 8001

# دستور اجرای سرویس
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
