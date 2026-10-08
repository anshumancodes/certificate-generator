from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import GenerationJob


def test_validation_missing_required_fields(client: TestClient, db_session: Session):
    payload = {
        "certificate_title": "Certificate of Completion",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None


def test_validation_invalid_email(client: TestClient, db_session: Session):
    payload = {
        "event_name": "Python Summit",
        "certificate_title": "Certificate of Completion",
        "recipients": [{"name": "Alice", "email": "not-a-valid-email"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None


def test_validation_empty_recipient_list(client: TestClient, db_session: Session):
    payload = {
        "event_name": "Python Summit",
        "certificate_title": "Certificate of Completion",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None


def test_validation_empty_or_whitespace_recipient_name(client: TestClient, db_session: Session):
    payload = {
        "event_name": "Python Summit",
        "certificate_title": "Certificate of Completion",
        "recipients": [{"name": "   ", "email": "alice@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None


def test_validation_name_too_long(client: TestClient, db_session: Session):
    payload = {
        "event_name": "Python Summit",
        "certificate_title": "Certificate of Completion",
        "recipients": [{"name": "A" * 256, "email": "alice@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None


def test_validation_too_many_recipients(client: TestClient, db_session: Session, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "MAX_RECIPIENTS_PER_JOB", 2)

    payload = {
        "event_name": "Python Summit",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

    count = db_session.scalar(select(GenerationJob))
    assert count is None
