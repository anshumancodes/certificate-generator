from collections.abc import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_db_session(db: Session = Depends(get_db)) -> Generator[Session, None, None]:
    return db
