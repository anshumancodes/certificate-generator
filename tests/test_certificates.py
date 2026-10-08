import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import GenerationJob, JobStatus


def test_download_completed_certificate(client: TestClient):
    payload = {
        "event_name": "API Design",
        "certificate_title": "Certificate of Completion",
        "recipients": [{"name": "Grace Hopper", "email": "grace@example.com"}],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    cert = certs_res.json()["certificates"][0]
    cert_id = cert["id"]

    download_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert "grace-hopper-certificate.pdf" in download_res.headers.get("content-disposition", "")
    assert download_res.content.startswith(b"%PDF")


def test_download_nonexistent_certificate(client: TestClient):
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/certificates/{random_id}")
    assert res.status_code == 404
    assert res.json() == {"detail": "Certificate not found"}


def test_download_pending_certificate_returns_409(client: TestClient, db_session: Session):
    job = GenerationJob(
        id=uuid.uuid4(),
        event_name="Workshop",
        certificate_title="Certificate",
        status=JobStatus.QUEUED,
        total_count=1,
    )
    cert = Certificate(
        id=uuid.uuid4(),
        job_id=job.id,
        recipient_name="Pending User",
        recipient_email="pending@example.com",
        status=CertificateStatus.PENDING,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    res = client.get(f"/api/v1/certificates/{cert.id}")
    assert res.status_code == 409
    assert "Certificate is not ready for download" in res.json()["detail"]


def test_list_certificates_nonexistent_job(client: TestClient):
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/jobs/{random_id}/certificates")
    assert res.status_code == 404
    assert res.json() == {"detail": "Job not found"}
