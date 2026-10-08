import uuid
from pydantic import BaseModel, ConfigDict


class CertificateSummary(BaseModel):
    id: uuid.UUID
    recipient_name: str
    recipient_email: str
    status: str
    download_url: str | None = None
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CertificateListResponse(BaseModel):
    job_id: uuid.UUID
    certificates: list[CertificateSummary]
