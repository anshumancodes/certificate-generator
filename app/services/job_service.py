import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import GenerationJob, JobStatus
from app.schemas.job import CreateJobRequest


def create_job(db: Session, request: CreateJobRequest) -> GenerationJob:
    job = GenerationJob(
        id=uuid.uuid4(),
        event_name=request.event_name,
        certificate_title=request.certificate_title,
        issue_date=request.issue_date,
        status=JobStatus.QUEUED,
        total_count=len(request.recipients),
        completed_count=0,
        failed_count=0,
    )
    db.add(job)

    certificates = [
        Certificate(
            id=uuid.uuid4(),
            job_id=job.id,
            recipient_name=rec.name,
            recipient_email=rec.email,
            status=CertificateStatus.PENDING,
        )
        for rec in request.recipients
    ]
    db.add_all(certificates)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: uuid.UUID) -> GenerationJob | None:
    stmt = select(GenerationJob).where(GenerationJob.id == job_id)
    return db.scalar(stmt)


def list_job_certificates(db: Session, job_id: uuid.UUID) -> list[Certificate]:
    stmt = (
        select(Certificate)
        .where(Certificate.job_id == job_id)
        .order_by(Certificate.created_at)
    )
    return list(db.scalars(stmt).all())


def mark_job_started(db: Session, job_id: uuid.UUID) -> None:
    db.execute(
        update(GenerationJob)
        .where(GenerationJob.id == job_id)
        .values(
            status=JobStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def finalize_job(db: Session, job_id: uuid.UUID) -> GenerationJob | None:
    job = get_job(db, job_id)
    if not job:
        return None

    if job.failed_count == 0:
        final_status = JobStatus.COMPLETED
    elif job.completed_count == 0:
        final_status = JobStatus.FAILED
    else:
        final_status = JobStatus.COMPLETED_WITH_ERRORS

    job.status = final_status
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
