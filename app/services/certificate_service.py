import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import GenerationJob


def get_certificate(db: Session, certificate_id: uuid.UUID) -> Certificate | None:
    stmt = select(Certificate).where(Certificate.id == certificate_id)
    return db.scalar(stmt)


def mark_certificate_processing(db: Session, certificate_id: uuid.UUID) -> None:
    db.execute(
        update(Certificate)
        .where(Certificate.id == certificate_id)
        .values(status=CertificateStatus.PROCESSING)
    )
    db.commit()


def mark_certificate_completed(
    db: Session,
    certificate_id: uuid.UUID,
    job_id: uuid.UUID,
    file_path: str,
) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(Certificate)
        .where(Certificate.id == certificate_id)
        .values(
            status=CertificateStatus.COMPLETED,
            file_path=file_path,
            completed_at=now,
        )
    )
    db.execute(
        update(GenerationJob)
        .where(GenerationJob.id == job_id)
        .values(completed_count=GenerationJob.completed_count + 1)
    )
    db.commit()


def mark_certificate_failed(
    db: Session,
    certificate_id: uuid.UUID,
    job_id: uuid.UUID,
    error_message: str,
) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(Certificate)
        .where(Certificate.id == certificate_id)
        .values(
            status=CertificateStatus.FAILED,
            error_message=error_message,
            completed_at=now,
        )
    )
    db.execute(
        update(GenerationJob)
        .where(GenerationJob.id == job_id)
        .values(failed_count=GenerationJob.failed_count + 1)
    )
    db.commit()
