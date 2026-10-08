import uuid
from datetime import date
from pathlib import Path

from app.services.certificate_generator import (
    CertificateGenerationError,
    generate_certificate,
)


def test_generate_certificate_pdf(tmp_path: Path):
    cert_id = uuid.uuid4()
    recipient_name = "Diana Prince"
    recipient_email = "diana@example.com"
    event_name = "Advanced System Design"
    certificate_title = "Certificate of Excellence"
    issue_date = date(2026, 10, 7)

    output_path = generate_certificate(
        certificate_id=cert_id,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        event_name=event_name,
        certificate_title=certificate_title,
        issue_date=issue_date,
        output_dir=tmp_path,
    )

    assert output_path.exists()
    assert output_path.is_file()
    assert output_path.name == f"{cert_id}.pdf"

    content = output_path.read_bytes()
    assert content.startswith(b"%PDF")
    assert len(content) > 1000

    assert b"Diana Prince" in content or b"Diana" in content


def test_generate_certificate_deliberate_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FAIL_RECIPIENTS", "FailUser")

    try:
        generate_certificate(
            certificate_id=uuid.uuid4(),
            recipient_name="FailUser",
            recipient_email="fail@example.com",
            event_name="Workshop",
            certificate_title="Certificate",
            output_dir=tmp_path,
        )
        assert False, "Expected CertificateGenerationError"
    except CertificateGenerationError as exc:
        assert "Simulated generation failure" in str(exc)
