import re
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.certificate import CertificateStatus
from app.services import certificate_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def slugify_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-")
    return slug or "recipient"


@router.get(
    "/{certificate_id}",
    summary="Download a generated certificate PDF",
    response_class=FileResponse,
)
def download_certificate(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> FileResponse:
    cert = certificate_service.get_certificate(db, certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    if cert.status != CertificateStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate is not ready for download. Current status: {cert.status}",
        )

    if not cert.file_path or not Path(cert.file_path).is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found on disk",
        )

    safe_name = slugify_filename(cert.recipient_name)
    download_filename = f"{safe_name}-certificate.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=download_filename,
    )
