import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.certificate import CertificateListResponse, CertificateSummary
from app.schemas.job import (
    CertificateProgressCounts,
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
)
from app.services import job_service
from app.workers.certificate_worker import process_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=CreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
)
def create_generation_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
) -> CreateJobResponse:
    job = job_service.create_job(db, request)
    background_tasks.add_task(process_job, job.id)
    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get generation job status and progress",
)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> JobStatusResponse:
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    pending_count = max(0, job.total_count - job.completed_count - job.failed_count)
    progress_pct = (
        round((job.completed_count / job.total_count) * 100.0, 2)
        if job.total_count > 0
        else 0.0
    )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
        completed=job.completed_count,
        failed=job.failed_count,
        pending=pending_count,
        progress_percent=progress_pct,
        certificates=CertificateProgressCounts(
            completed=job.completed_count,
            failed=job.failed_count,
            pending=pending_count,
        ),
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=CertificateListResponse,
    summary="List certificates belonging to a generation job",
)
def list_job_certificates(
    job_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> CertificateListResponse:
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    certificates = job_service.list_job_certificates(db, job_id)
    summaries = [
        CertificateSummary(
            id=cert.id,
            recipient_name=cert.recipient_name,
            recipient_email=cert.recipient_email,
            status=cert.status,
            download_url=(
                f"/api/v1/certificates/{cert.id}"
                if cert.status == "completed"
                else None
            ),
            error=cert.error_message if cert.status == "failed" else None,
        )
        for cert in certificates
    ]

    return CertificateListResponse(
        job_id=job.id,
        certificates=summaries,
    )
