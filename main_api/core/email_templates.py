from html import escape


def build_reset_code_email_html(code: str) -> str:
    return f"""
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


def build_feeder_offline_email_html(feeder_name: str, feeder_id: int, consecutive_failures: int) -> str:
    return f"""
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
                color: #c62828;
                margin: 0;
            }}
            .badge-box {{
                text-align: center;
                margin: 25px 0;
            }}
            .badge {{
                display: inline-block;
                font-size: 18px;
                font-weight: bold;
                color: #c62828;
                background-color: #fdecea;
                padding: 10px 24px;
                border-radius: 6px;
                border: 1px dashed #ef9a9a;
            }}
            .meta {{
                font-size: 13px;
                color: #555;
                background-color: #f8f9fa;
                border-radius: 6px;
                padding: 12px 16px;
                margin-top: 15px;
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
                <h2>⚠️ هشدار قطعی فیدر</h2>
            </div>
            <p>سلام،</p>
            <p>فیدر زیر پس از چند بار عدم پاسخ‌دهی، آفلاین علامت‌گذاری شد:</p>

            <div class="badge-box">
                <span class="badge">{feeder_name}</span>
            </div>

            <div class="meta">
                شناسه فیدر: {feeder_id}<br>
                تعداد تلاش‌های ناموفق متوالی: {consecutive_failures}
            </div>

            <p style="margin-top: 20px;">لطفاً در صورت نیاز وضعیت اتصال این فیدر را بررسی کنید.</p>

            <div class="footer">
                سامانه پایش مصرف انرژی (Power Monitoring)
            </div>
        </div>
    </body>
    </html>
    """


def _card_email_html(heading: str, color: str, intro: str, badge: str, meta_lines: list, note: str) -> str:
    meta_html = "<br>".join(escape(str(line)) for line in meta_lines)
    return f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Tahoma, 'Vazir', Arial, sans-serif; background-color: #f4f6f8; margin: 0;
                 padding: 20px; color: #333; direction: rtl; text-align: right;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px;
                    border: 1px solid #e1e4e8;">
            <h2 style="text-align: center; color: {color}; margin: 0 0 20px;">{escape(heading)}</h2>
            <p>{escape(intro)}</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="display: inline-block; font-size: 20px; font-weight: bold; color: {color};
                             background-color: #f8f9fa; padding: 10px 24px; border-radius: 6px;
                             border: 1px dashed {color}; letter-spacing: 2px;">{escape(badge)}</span>
            </div>
            <div style="font-size: 13px; color: #555; background-color: #f8f9fa; border-radius: 6px;
                        padding: 12px 16px;">{meta_html}</div>
            <p style="margin-top: 20px;">{escape(note)}</p>
            <div style="font-size: 12px; color: #888; margin-top: 30px; border-top: 1px solid #eee;
                        padding-top: 15px; text-align: center;">سامانه پایش مصرف انرژی (Power Monitoring)</div>
        </div>
    </body>
    </html>
    """


def build_load_alert_email_html(entity_label: str, entity_name: str, status_label: str, is_critical: bool,
                                meta_lines: list) -> str:
    return _card_email_html(
        heading=f"{'🚨' if is_critical else '⚠️'} وضعیت {status_label} {entity_label}",
        color="#c62828" if is_critical else "#ef6c00",
        intro=f"جریان {entity_label} زیر از حد مجاز تعیین‌شده در تنظیمات سامانه عبور کرد:",
        badge=entity_name,
        meta_lines=meta_lines,
        note="لطفاً وضعیت بار را بررسی کنید.",
    )


def build_command_code_email_html(code: str, feeder_name: str, action_label: str, expires_seconds: int) -> str:
    return _card_email_html(
        heading="🔐 کد تأیید فرمان",
        color="#1565c0",
        intro=f"برای اجرای فرمان «{action_label}» روی فیدر «{feeder_name}» کد زیر را وارد کنید:",
        badge=code,
        meta_lines=[f"اعتبار کد: {expires_seconds} ثانیه"],
        note="اگر این فرمان را شما درخواست نکرده‌اید، فوراً به مدیر سامانه اطلاع دهید.",
    )
