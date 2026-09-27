import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

EXPORT_TIMEOUT_SECONDS = 60.0

MAX_EXCEL_ROWS = 500_000
MAX_PDF_ROWS = 5_000

COLUMNS: List[tuple] = [
    ("timestamp", "Timestamp"),
    ("voltage", "Voltage (V)"),
    ("current", "Current (A)"),
    ("active_power", "Active Power (W)"),
    ("reactive_power", "Reactive Power (VAr)"),
    ("power_factor", "Power Factor"),
    ("frequency", "Frequency (Hz)"),
]
COLUMN_KEYS = [key for key, _ in COLUMNS]

ENERGY_COLUMNS: List[tuple] = [
    ("feeder_id", "Feeder ID"),
    ("feeder_name", "Feeder"),
    ("role", "Type"),
    ("active_energy_kwh", "Active Energy (kWh)"),
    ("reactive_energy_kvarh", "Reactive Energy (kVARh)"),
]


@dataclass
class ReportSection:
    title: str
    records: List[Dict[str, Any]]

    @property
    def sheet_title(self) -> str:
        return re.sub(r"[\\/*?:\[\]]", "_", self.title)[:31]


def _clean_timestamp(ts: Any) -> str:
    if not ts:
        return ""
    return str(ts).replace("T", " ").split("+")[0].split(".")[0]


def resolve_columns(requested: Optional[Sequence[str]]) -> List[tuple]:
    if not requested:
        return COLUMNS
    unknown = [c for c in requested if c not in COLUMN_KEYS]
    if unknown:
        raise ValueError(f"ستون نامعتبر: {', '.join(unknown)} (مجاز: {', '.join(COLUMN_KEYS)})")
    wanted = set(requested) | {"timestamp"}
    return [col for col in COLUMNS if col[0] in wanted]


def _cell(row: Dict[str, Any], key: str) -> Any:
    return _clean_timestamp(row.get("timestamp")) if key == "timestamp" else row.get(key, "")


def build_excel_report(sections: List[ReportSection], columns: List[tuple] = COLUMNS,
                       energy: Optional[List[Dict[str, Any]]] = None) -> BytesIO:
    workbook = Workbook(write_only=True)
    if energy:
        summary = workbook.create_sheet(title="Energy Summary")
        summary.append([label for _, label in ENERGY_COLUMNS])
        for row in energy:
            summary.append([row.get(key, "") for key, _ in ENERGY_COLUMNS])

    for section in sections:
        sheet = workbook.create_sheet(title=section.sheet_title)
        sheet.append([label for _, label in columns])
        for row in section.records:
            sheet.append([_cell(row, key) for key, _ in columns])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_pdf_report(sections: List[ReportSection], start: str, stop: str, columns: List[tuple] = COLUMNS,
                     energy: Optional[List[Dict[str, Any]]] = None) -> BytesIO:
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
    elements = [
        Paragraph("Feeder Telemetry Report", styles["Title"]),
        Paragraph(f"Range: {start} &rarr; {stop} | Generated at: {datetime.utcnow().isoformat()}Z", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    if energy:
        elements.append(Paragraph("Energy Summary", styles["Heading2"]))
        rows = [[label for _, label in ENERGY_COLUMNS]] + [
            [str(row.get(key, "")) for key, _ in ENERGY_COLUMNS] for row in energy
        ]
        elements.extend([_styled_table(rows), Spacer(1, 0.5 * cm)])

    for section in sections:
        elements.append(Paragraph(f"{section.title} - records: {len(section.records)}", styles["Heading2"]))
        rows = [[label for _, label in columns]] + [
            [str(_cell(row, key)) for key, _ in columns] for row in section.records
        ]
        elements.extend([_styled_table(rows), Spacer(1, 0.5 * cm)])

    doc.build(elements)
    output.seek(0)
    return output


def _styled_table(rows: List[List[str]]) -> Table:
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]))
    return table
