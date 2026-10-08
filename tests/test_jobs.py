import uuid
from fastapi.testclient import TestClient


def test_create_generation_job_success(client: TestClient):
    payload = {
        "event_name": "Backend Engineering Workshop",
        "certificate_title": "Certificate of Completion",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Smith", "email": "bob@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "job_id" in data
    assert data["status"] in ["queued", "processing", "completed"]
    assert data["total"] == 2

    job_id = data["job_id"]
    status_response = client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200

    status_data = status_response.json()
    assert status_data["job_id"] == job_id
    assert status_data["total"] == 2
    assert status_data["completed"] == 2
    assert status_data["failed"] == 0
    assert status_data["pending"] == 0
    assert status_data["progress_percent"] == 100.0


def test_get_nonexistent_job(client: TestClient):
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
