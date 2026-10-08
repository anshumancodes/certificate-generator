from datetime import date
from sqlalchemy.orm import Session

from app.models.job import JobStatus
from app.schemas.job import CreateJobRequest, RecipientInput
from app.services import certificate_service, job_service


def test_job_progress_lifecycle(db_session: Session):
    request = CreateJobRequest(
        event_name="Cloud Architecture Workshop",
        certificate_title="Certificate of Completion",
        issue_date=date(2026, 10, 7),
        recipients=[
            RecipientInput(name="User One", email="one@example.com"),
            RecipientInput(name="User Two", email="two@example.com"),
            RecipientInput(name="User Three", email="three@example.com"),
        ],
    )

    job = job_service.create_job(db_session, request)
    assert job.status == JobStatus.QUEUED
    assert job.total_count == 3
    assert job.completed_count == 0
    assert job.failed_count == 0

    job_service.mark_job_started(db_session, job.id)
    db_session.refresh(job)
    assert job.status == JobStatus.PROCESSING
    assert job.started_at is not None

    certs = job_service.list_job_certificates(db_session, job.id)
    assert len(certs) == 3

    certificate_service.mark_certificate_completed(
        db=db_session,
        certificate_id=certs[0].id,
        job_id=job.id,
        file_path="/tmp/one.pdf",
    )
    db_session.refresh(job)
    assert job.completed_count == 1
    assert job.failed_count == 0

    certificate_service.mark_certificate_failed(
        db=db_session,
        certificate_id=certs[1].id,
        job_id=job.id,
        error_message="Font rendering failed",
    )
    db_session.refresh(job)
    assert job.completed_count == 1
    assert job.failed_count == 1

    certificate_service.mark_certificate_completed(
        db=db_session,
        certificate_id=certs[2].id,
        job_id=job.id,
        file_path="/tmp/three.pdf",
    )
    db_session.refresh(job)
    assert job.completed_count == 2
    assert job.failed_count == 1

    final_job = job_service.finalize_job(db_session, job.id)
    assert final_job is not None
    assert final_job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert final_job.completed_at is not None

    progress_percent = round((final_job.completed_count / final_job.total_count) * 100.0, 2)
    assert progress_percent == 66.67
