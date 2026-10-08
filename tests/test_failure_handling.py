from fastapi.testclient import TestClient


def test_failure_isolation_in_batch(client: TestClient, monkeypatch):
    monkeypatch.setenv("FAIL_RECIPIENTS", "Bob Smith")

    payload = {
        "event_name": "Distributed Systems",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Smith", "email": "bob@example.com"},
            {"name": "Charlie Brown", "email": "charlie@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_res = client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()

    assert job_data["status"] == "completed_with_errors"
    assert job_data["total"] == 3
    assert job_data["completed"] == 2
    assert job_data["failed"] == 1
    assert job_data["pending"] == 0

    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    certs_data = certs_res.json()["certificates"]
    assert len(certs_data) == 3

    alice_cert = next(c for c in certs_data if c["recipient_name"] == "Alice Johnson")
    bob_cert = next(c for c in certs_data if c["recipient_name"] == "Bob Smith")
    charlie_cert = next(c for c in certs_data if c["recipient_name"] == "Charlie Brown")

    assert alice_cert["status"] == "completed"
    assert alice_cert["download_url"] is not None
    assert alice_cert["error"] is None

    assert bob_cert["status"] == "failed"
    assert bob_cert["download_url"] is None
    assert bob_cert["error"] is not None
    assert "Simulated generation failure" in bob_cert["error"]

    assert charlie_cert["status"] == "completed"
    assert charlie_cert["download_url"] is not None
    assert charlie_cert["error"] is None

    alice_download = client.get(alice_cert["download_url"])
    assert alice_download.status_code == 200
    assert alice_download.headers["content-type"] == "application/pdf"

    charlie_download = client.get(charlie_cert["download_url"])
    assert charlie_download.status_code == 200
    assert charlie_download.headers["content-type"] == "application/pdf"

    bob_download = client.get(f"/api/v1/certificates/{bob_cert['id']}")
    assert bob_download.status_code == 409
    assert "Certificate is not ready for download" in bob_download.json()["detail"]
