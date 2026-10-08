import os
from collections.abc import Generator
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.workers.certificate_worker import set_worker_session_factory


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_engine, test_session_factory) -> Generator[Session, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tmp_cert_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    certs_dir = tmp_path / "test_generated"
    certs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "GENERATED_CERTIFICATES_DIR", str(certs_dir))
    monkeypatch.setenv("GENERATED_CERTIFICATES_DIR", str(certs_dir))
    return certs_dir


@pytest.fixture
def client(
    db_session: Session,
    test_session_factory,
    tmp_cert_dir: Path,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    set_worker_session_factory(test_session_factory)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    set_worker_session_factory(None)
