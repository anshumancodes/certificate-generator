import uuid
from collections.abc import Callable
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.certificate_generator import generate_certificate
from app.services.certificate_service import (
    mark_certificate_completed,
    mark_certificate_failed,
    mark_certificate_processing,
)
from app.services.job_service import (
    finalize_job,
    get_job,
    list_job_certificates,
    mark_job_started,
)

_worker_session_factory: Callable[[], Session] | None = None


def set_worker_session_factory(factory: Callable[[], Session] | None) -> None:
    global _worker_session_factory
    _worker_session_factory = factory


def get_worker_session_factory() -> Callable[[], Session]:
    return _worker_session_factory or SessionLocal


def process_job(
    job_id: uuid.UUID,
    db_session_factory: Callable[[], Session] | None = None,
) -> None:
    session_factory = db_session_factory or get_worker_session_factory()
    db: Session = session_factory()
    try:
        job = get_job(db, job_id)
        if not job:
            return

        mark_job_started(db, job_id)
        certificates = list_job_certificates(db, job_id)

        for cert in certificates:
            mark_certificate_processing(db, cert.id)
            try:
                pdf_path = generate_certificate(
                    certificate_id=cert.id,
                    recipient_name=cert.recipient_name,
                    recipient_email=cert.recipient_email,
                    event_name=job.event_name,
                    certificate_title=job.certificate_title,
                    issue_date=job.issue_date,
                )
                mark_certificate_completed(
                    db=db,
                    certificate_id=cert.id,
                    job_id=job.id,
                    file_path=str(pdf_path),
                )
            except Exception as exc:
                mark_certificate_failed(
                    db=db,
                    certificate_id=cert.id,
                    job_id=job.id,
                    error_message=str(exc),
                )

        finalize_job(db, job_id)
    finally:
        db.close()
