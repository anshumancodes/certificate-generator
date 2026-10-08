import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings


class RecipientInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Recipient name cannot be empty or whitespace only")
        return trimmed


class CreateJobRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=255)
    certificate_title: str = Field(..., min_length=1, max_length=255)
    issue_date: date | None = None
    recipients: list[RecipientInput] = Field(..., min_length=1)

    @field_validator("event_name", "certificate_title")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace only")
        return trimmed

    @field_validator("recipients")
    @classmethod
    def validate_recipients_max_length(cls, v: list[RecipientInput]) -> list[RecipientInput]:
        if len(v) > settings.MAX_RECIPIENTS_PER_JOB:
            raise ValueError(
                f"Number of recipients exceeds maximum allowed ({settings.MAX_RECIPIENTS_PER_JOB})"
            )
        return v


class CreateJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total: int


class CertificateProgressCounts(BaseModel):
    completed: int
    failed: int
    pending: int


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total: int
    completed: int
    failed: int
    pending: int
    progress_percent: float
    certificates: CertificateProgressCounts
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
