import smtplib
from email.message import EmailMessage
from main_api.core.config import settings


def send_reset_password_email(email_to: str, reset_token: str):
    # لینک فرانت‌اند که توکن به آن متصل می‌شود
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    msg = EmailMessage()
    msg['Subject'] = "بازیابی رمز عبور"
    msg['From'] = settings.SMTP_USERNAME
    msg['To'] = email_to

    # متن ایمیل (می‌توانید HTML هم قرار دهید)
    msg.set_content(f"""
    شما درخواست بازیابی رمز عبور داده‌اید.
    برای تغییر رمز عبور خود روی لینک زیر کلیک کنید:

    {reset_link}

    اگر شما این درخواست را نداده‌اید، این ایمیل را نادیده بگیرید.
    """)

    try:
        # اتصال امن به SMTP جیمیل
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        # در محیط پروداکشن اینجا باید خطا را لاگ کنید
