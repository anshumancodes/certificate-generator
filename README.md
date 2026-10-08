# Bulk Certificate Generator API

## Overview

Bulk Certificate Generator API is a production-quality backend service built with Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, and ReportLab. It accepts a single bulk certificate request containing multiple recipients, validates input immediately, creates tracked database records, and processes PDF generation asynchronously in the background. Individual generation failures are completely isolated so that errors for one recipient never abort processing for others. Clients can monitor job progress in real time and download completed PDF certificates.

## Architecture

The system follows a clean separation of concerns across API, database, business logic, PDF generation, and background processing layers.

```
Client
  |
  v
POST /api/v1/jobs
  |
  v
Validate request (Pydantic)
  |
  v
Create Job + Certificate records (DB transaction)
  |
  v
Return 202 Accepted + job_id
  |
  v
Background Worker
  |
  +-> Certificate 1 -> Generate PDF -> Completed
  |
  +-> Certificate 2 -> Generate PDF -> Completed
  |
  +-> Certificate 3 -> Failure isolated -> Marked Failed
  |
  v
Finalize Job (completed / completed_with_errors / failed)
```

### Why Background Processing Was Chosen

PDF generation involves document layout calculation, vector drawing, and disk I/O. For a batch of 50 to 500 recipients, synchronous processing inside a single HTTP request would block the HTTP connection for seconds or minutes, leading to gateway timeouts (504 Gateway Timeout), connection drops, and poor client experience. Background processing decouples the acceptance of work from its execution, giving clients an immediate HTTP 202 response with a job ID while offloading rendering to background execution.

### How Individual Failures Are Isolated

Each certificate in a batch is wrapped in its own isolated exception handling block inside the worker loop:

1. The worker marks the certificate status as processing.
2. The generator function generates the PDF.
3. If successful, the certificate is marked completed with its file path, and the job completed count is incremented atomically in SQL (`completed_count = completed_count + 1`).
4. If an exception occurs, the certificate is marked failed with a descriptive error message, and the job failed count is incremented atomically in SQL (`failed_count = failed_count + 1`).
5. Execution immediately proceeds to the next recipient without interruption.
6. When all recipients finish, the job transitions to `completed` (0 failures), `completed_with_errors` (partial failures), or `failed` (all failed).

### Why Certificate Generation Is Separated from the HTTP Layer

The certificate generation service (`app/services/certificate_generator.py`) is written as a pure business function. It has zero dependencies on FastAPI, HTTP request objects, or database sessions. It takes recipient and event attributes and returns a file path or raises a typed error. This provides key architectural advantages:

* Unit testability without spinning up mock HTTP servers or web clients.
* Reusability across different delivery mechanisms (HTTP API, CLI tools, event consumers).
* Painless migration to dedicated task queues.

### Scaling Path to Celery or RQ

The worker abstraction (`app/workers/certificate_worker.py`) is decoupled from FastAPI. Migrating to Celery or RQ requires zero changes to the generation logic or database models:

1. Replace `background_tasks.add_task(process_job, job.id)` in the route with `celery_app.send_task("process_job", args=[str(job.id)])`.
2. For very large batches (e.g. 10,000+ recipients), divide certificate IDs into chunks and enqueue individual Celery tasks per chunk.
3. Because counter increments use atomic SQL updates (`completed_count = completed_count + 1`), multiple distributed workers can update the parent job record concurrently without lost updates or race conditions.
4. Replace local filesystem storage with S3 or Google Cloud Storage, updating `file_path` to an object key and generating pre-signed URLs for downloads.

## Validation Behavior

The system maintains a strict distinction between request-level validation errors and individual generation failures:

### Request-Level Validation Errors

Occur synchronously during HTTP request handling before any database record is created:
* Missing required fields (`event_name`, `certificate_title`, `recipients`)
* Invalid email formats
* Empty recipient names or whitespace-only strings
* Field lengths exceeding 255 characters
* Empty recipient lists
* Exceeding maximum allowed recipients per request (`MAX_RECIPIENTS_PER_JOB`)

Outcome: HTTP 422 Unprocessable Entity with detailed field-level validation errors. No database records or background jobs are created.

### Individual Generation Failures

Occur asynchronously after the job has been accepted and persisted in the database:
* PDF rendering errors, template font issues, or storage write errors
* Simulated failure triggers during testing

Outcome: Only the affected certificate is marked failed with its error message recorded. Other certificates continue processing, and the job finishes with status `completed_with_errors`.

## Database Schema

### GenerationJob (`generation_jobs`)
* `id` (UUID, Primary Key)
* `event_name` (VARCHAR(255), NOT NULL)
* `certificate_title` (VARCHAR(255), NOT NULL)
* `issue_date` (DATE, NULLABLE)
* `status` (VARCHAR(30), DEFAULT 'queued', Indexed) - queued, processing, completed, completed_with_errors, failed
* `total_count` (INTEGER, NOT NULL)
* `completed_count` (INTEGER, DEFAULT 0)
* `failed_count` (INTEGER, DEFAULT 0)
* `created_at` (TIMESTAMPTZ, Indexed)
* `started_at` (TIMESTAMPTZ, NULLABLE)
* `completed_at` (TIMESTAMPTZ, NULLABLE)

### Certificate (`certificates`)
* `id` (UUID, Primary Key)
* `job_id` (UUID, Foreign Key referencing `generation_jobs.id` ON DELETE CASCADE, Indexed)
* `recipient_name` (VARCHAR(255), NOT NULL)
* `recipient_email` (VARCHAR(255), NOT NULL)
* `status` (VARCHAR(20), DEFAULT 'pending', Indexed) - pending, processing, completed, failed
* `file_path` (TEXT, NULLABLE)
* `error_message` (TEXT, NULLABLE)
* `created_at` (TIMESTAMPTZ)
* `completed_at` (TIMESTAMPTZ, NULLABLE)
* Composite index: `(job_id, status)`

## Setup and Installation

### Prerequisites
* Python 3.12+
* Docker and Docker Compose

### 1. Clone Repository and Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Start PostgreSQL Database
```bash
docker compose up -d
```

### 4. Apply Database Migrations
```bash
alembic upgrade head
```

### 5. Start the Application
```bash
uvicorn app.main:app --reload
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## Running Tests

Run the complete automated test suite with pytest:

```bash
pytest -v
```

The test suite runs against an isolated SQLite test database with temporary file directories and does not affect your production database or filesystem.

## API Examples

### 1. Create a Generation Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Backend Engineering Workshop",
    "certificate_title": "Certificate of Completion",
    "issue_date": "2026-10-07",
    "recipients": [
      {
        "name": "Alice Johnson",
        "email": "alice@example.com"
      },
      {
        "name": "Bob Smith",
        "email": "bob@example.com"
      }
    ]
  }'
```

Response (HTTP 202 Accepted):
```json
{
  "job_id": "c1f76d4e-1234-4567-89ab-cdef01234567",
  "status": "queued",
  "total": 2
}
```

### 2. Check Job Status
```bash
curl -X GET http://localhost:8000/api/v1/jobs/c1f76d4e-1234-4567-89ab-cdef01234567
```

Response (HTTP 200 OK):
```json
{
  "job_id": "c1f76d4e-1234-4567-89ab-cdef01234567",
  "status": "completed",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "pending": 0,
  "progress_percent": 100.0,
  "certificates": {
    "completed": 2,
    "failed": 0,
    "pending": 0
  },
  "created_at": "2026-10-07T12:00:00Z",
  "started_at": "2026-10-07T12:00:01Z",
  "completed_at": "2026-10-07T12:00:02Z"
}
```

### 3. List Job Certificates
```bash
curl -X GET http://localhost:8000/api/v1/jobs/c1f76d4e-1234-4567-89ab-cdef01234567/certificates
```

Response (HTTP 200 OK):
```json
{
  "job_id": "c1f76d4e-1234-4567-89ab-cdef01234567",
  "certificates": [
    {
      "id": "e8a12345-6789-abcd-ef01-23456789abcd",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "completed",
      "download_url": "/api/v1/certificates/e8a12345-6789-abcd-ef01-23456789abcd",
      "error": null
    },
    {
      "id": "f9b23456-789a-bcde-f012-3456789abcde",
      "recipient_name": "Bob Smith",
      "recipient_email": "bob@example.com",
      "status": "completed",
      "download_url": "/api/v1/certificates/f9b23456-789a-bcde-f012-3456789abcde",
      "error": null
    }
  ]
}
```

### 4. Download a Certificate
```bash
curl -O -J http://localhost:8000/api/v1/certificates/e8a12345-6789-abcd-ef01-23456789abcd
```

Response:
* HTTP 200 OK
* Content-Type: application/pdf
* Content-Disposition: attachment; filename="alice-johnson-certificate.pdf"
