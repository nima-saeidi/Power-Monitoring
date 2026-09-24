"""
ساخت خروجی گزارش تله‌متری (اکسل / PDF) از داده‌های تاریخی یک فیدر.
داده‌ی ورودی همان ساختاری است که TelemetryService.get_history برمی‌گرداند
(لیستی از رکوردهای TelemetryResponse: feeder_id, voltage, current, active_power,
reactive_power, power_factor, frequency, timestamp).

نکته‌ی کارایی: فیدرهایی که مدت طولانی پایش شده‌اند می‌توانند میلیون‌ها رکورد
تله‌متری داشته باشند. به همین دلیل:
- خروجی اکسل با حالت streaming (openpyxl write_only) ساخته می‌شود تا کل داده در
  حافظه به‌صورت اشیاء Cell/Row نگه داشته نشود (بر خلاف pandas.to_excel که تمام
  DataFrame + تمام سلول‌های استایل‌دار را قبل از نوشتن در حافظه می‌سازد).
- خروجی PDF (که بر خلاف اکسل برای نمایش/چاپ است، نه پردازش داده‌ی خام) با سقف
  MAX_PDF_ROWS محدود می‌شود؛ رندر چند صدهزار ردیف در یک جدول PDF عملاً غیرقابل
  استفاده و بسیار کند/پرمصرف حافظه است. برای داده‌ی خام بزرگ باید از اکسل
  استفاده شود.
"""
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# timeout (ثانیه) درخواست به میکروسرویس تله‌متری مخصوص گزارش‌گیری؛ بزرگ‌تر از
# timeout حالت نمایش زنده (chart/history) چون کوئری InfluxDB روی بازه‌های بزرگ کندتر است
EXPORT_TIMEOUT_SECONDS = 60.0

# سقف تعداد ردیف قابل خروجی گرفتن در هر فرمت (محافظت در برابر درخواست‌های
# سنگین/پاتولوژیک که می‌توانند حافظه/CPU سرور را قفل کنند)
MAX_EXCEL_ROWS = 500_000
MAX_PDF_ROWS = 5_000

# ترتیب و عنوان ستون‌ها برای هر دو خروجی
COLUMNS: List[tuple] = [
    ("timestamp", "Timestamp"),
    ("voltage", "Voltage (V)"),
    ("current", "Current (A)"),
    ("active_power", "Active Power (W)"),
    ("reactive_power", "Reactive Power (VAr)"),
    ("power_factor", "Power Factor"),
    ("frequency", "Frequency (Hz)"),
]


def _clean_timestamp(ts: Any) -> str:
    if not ts:
        return ""
    return str(ts).replace("T", " ").split("+")[0].split(".")[0]


def build_excel_report(feeder_id: int, records: List[Dict[str, Any]]) -> BytesIO:
    """
    ساخت فایل اکسل (.xlsx) با حالت streaming (write_only) از رکوردهای تله‌متری
    یک فیدر؛ برای دیتاست‌های بزرگ (صدها هزار ردیف) به‌صورت قابل‌قبول سریع و
    کم‌مصرف از نظر حافظه است چون هر ردیف مستقیماً نوشته و آزاد می‌شود.
    """
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title=f"Feeder_{feeder_id}")
    sheet.append([label for _, label in COLUMNS])

    for row in records:
        sheet.append([
            _clean_timestamp(row.get("timestamp")) if key == "timestamp" else row.get(key, "")
            for key, _ in COLUMNS
        ])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_pdf_report(
    feeder_id: int,
    records: List[Dict[str, Any]],
    start: str,
    stop: str,
) -> BytesIO:
    """ساخت فایل PDF از رکوردهای تله‌متری یک فیدر (جدول + خلاصه). سقف: MAX_PDF_ROWS"""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Feeder Telemetry Report - Feeder ID: {feeder_id}", styles["Title"]))
    elements.append(Paragraph(f"Range: {start} &rarr; {stop} | Generated at: {datetime.utcnow().isoformat()}Z", styles["Normal"]))
    elements.append(Paragraph(f"Total records: {len(records)}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    header = [label for _, label in COLUMNS]
    table_data = [header]
    for row in records:
        table_data.append([
            _clean_timestamp(row.get("timestamp")) if key == "timestamp" else str(row.get(key, ""))
            for key, _ in COLUMNS
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)
    return output
