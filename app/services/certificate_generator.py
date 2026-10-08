import os
import uuid
from datetime import date
from pathlib import Path
from reportlab.pdfgen import canvas

from app.core.config import settings
from templates.certificate_template import (
    BORDER_MARGIN_INNER,
    BORDER_MARGIN_OUTER,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    PAGE_HEIGHT,
    PAGE_WIDTH,
)


class CertificateGenerationError(Exception):
    pass


def generate_certificate(
    *,
    certificate_id: str | uuid.UUID,
    recipient_name: str,
    recipient_email: str,
    event_name: str,
    certificate_title: str,
    issue_date: date | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    fail_list = [
        item.strip()
        for item in os.getenv("FAIL_RECIPIENTS", "").split(",")
        if item.strip()
    ]
    if recipient_name in fail_list or recipient_email in fail_list:
        raise CertificateGenerationError(
            f"Simulated generation failure for recipient {recipient_name}"
        )

    target_dir = Path(output_dir) if output_dir else settings.certificates_dir_path
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{certificate_id}.pdf"

    try:
        c = canvas.Canvas(
            str(file_path),
            pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
            pageCompression=0,
        )
        center_x = PAGE_WIDTH / 2.0

        c.setStrokeColor(COLOR_PRIMARY)
        c.setLineWidth(3)
        c.rect(
            BORDER_MARGIN_OUTER,
            BORDER_MARGIN_OUTER,
            PAGE_WIDTH - (2 * BORDER_MARGIN_OUTER),
            PAGE_HEIGHT - (2 * BORDER_MARGIN_OUTER),
        )

        c.setStrokeColor(COLOR_SECONDARY)
        c.setLineWidth(1)
        c.rect(
            BORDER_MARGIN_INNER,
            BORDER_MARGIN_INNER,
            PAGE_WIDTH - (2 * BORDER_MARGIN_INNER),
            PAGE_HEIGHT - (2 * BORDER_MARGIN_INNER),
        )

        c.setFont("Helvetica-Bold", 26)
        c.setFillColor(COLOR_PRIMARY)
        c.drawCentredString(center_x, PAGE_HEIGHT - 120, certificate_title.upper())

        c.setFont("Helvetica", 13)
        c.setFillColor(COLOR_TEXT_MUTED)
        c.drawCentredString(center_x, PAGE_HEIGHT - 170, "This certifies that")

        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(COLOR_TEXT_DARK)
        c.drawCentredString(center_x, PAGE_HEIGHT - 220, recipient_name)

        name_width = c.stringWidth(recipient_name, "Helvetica-Bold", 24)
        c.setStrokeColor(COLOR_SECONDARY)
        c.setLineWidth(1.5)
        c.line(
            center_x - (name_width / 2.0) - 20,
            PAGE_HEIGHT - 228,
            center_x + (name_width / 2.0) + 20,
            PAGE_HEIGHT - 228,
        )

        c.setFont("Helvetica", 13)
        c.setFillColor(COLOR_TEXT_MUTED)
        c.drawCentredString(center_x, PAGE_HEIGHT - 275, "has successfully completed")

        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(COLOR_PRIMARY)
        c.drawCentredString(center_x, PAGE_HEIGHT - 325, event_name)

        formatted_date = (
            issue_date.strftime("%B %d, %Y")
            if issue_date
            else date.today().strftime("%B %d, %Y")
        )
        c.setFont("Helvetica", 12)
        c.setFillColor(COLOR_TEXT_DARK)
        c.drawCentredString(center_x, PAGE_HEIGHT - 380, formatted_date)

        c.setStrokeColor(COLOR_TEXT_MUTED)
        c.setLineWidth(0.5)
        c.line(center_x - 120, PAGE_HEIGHT - 420, center_x + 120, PAGE_HEIGHT - 420)

        c.setFont("Helvetica", 9)
        c.setFillColor(COLOR_TEXT_MUTED)
        c.drawCentredString(
            center_x,
            PAGE_HEIGHT - 440,
            f"Certificate ID: {certificate_id}",
        )

        c.showPage()
        c.save()
        return file_path
    except CertificateGenerationError:
        raise
    except Exception as exc:
        raise CertificateGenerationError(f"Failed to generate certificate PDF: {exc}") from exc
