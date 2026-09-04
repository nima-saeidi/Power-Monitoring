import smtplib
import logging
from email.message import EmailMessage
from main_api.core.config import settings

logger = logging.getLogger(__name__)


def send_reset_code_email(email_to: str, code: str):
    """
    ارسال کد ۶ رقمی تایید بازنشانی رمز عبور به ایمیل کاربر
    """
    msg = EmailMessage()
    msg['Subject'] = "کد تأیید بازیابی رمز عبور"
    msg['From'] = settings.SMTP_USERNAME
    msg['To'] = email_to

    # نسخه متنی ساده (Fallback)
    text_content = f"""
سلام،

درخواست بازیابی رمز عبور برای حساب شما ثبت شده است.
کد تأیید شما: {code}

این کد به مدت ۵ دقیقه معتبر است.
اگر شما این درخواست را نداده‌اید، لطفاً این ایمیل را نادیده بگیرید.
    """
    msg.set_content(text_content.strip())

    # نسخه HTML با استایل راست‌به‌چین (RTL)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, 'Vazir', Arial, sans-serif;
                background-color: #f4f6f8;
                margin: 0;
                padding: 20px;
                color: #333;
                direction: rtl;
                text-align: right;
            }}
            .container {{
                max-width: 500px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                border: 1px solid #e1e4e8;
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .header h2 {{
                color: #2c3e50;
                margin: 0;
            }}
            .code-box {{
                text-align: center;
                margin: 25px 0;
            }}
            .code {{
                display: inline-block;
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 6px;
                color: #1e88e5;
                background-color: #f0f7ff;
                padding: 10px 24px;
                border-radius: 6px;
                border: 1px dashed #90caf9;
                direction: ltr;
            }}
            .footer {{
                font-size: 12px;
                color: #888;
                margin-top: 30px;
                border-top: 1px solid #eee;
                padding-top: 15px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>بازیابی رمز عبور</h2>
            </div>
            <p>سلام،</p>
            <p>درخواست تغییر رمز عبور برای حساب کاربری شما ثبت شده است. برای ادامه فرآیند از کد تأیید زیر استفاده کنید:</p>

            <div class="code-box">
                <span class="code">{code}</span>
            </div>

            <p style="color: #e53935; font-size: 13px;">این کد به مدت ۵ دقیقه معتبر است.</p>
            <p>اگر شما این درخواست را ارسال نکرده‌اید، نیازی به انجام کاری نیست و حساب شما در امنیت است.</p>

            <div class="footer">
                سامانه پایش مصرف انرژی (Power Monitoring)
            </div>
        </div>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"کد بازیابی با موفقیت به ایمیل {email_to} ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال ایمیل به {email_to}: {str(e)}")
        # در صورت نیاز به بررسی دقیق‌تر خطا در کنسول:
        print(f"Error sending email: {e}")
