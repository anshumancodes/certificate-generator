from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/certificates"
    GENERATED_CERTIFICATES_DIR: str = "./generated"
    MAX_RECIPIENTS_PER_JOB: int = 500
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def certificates_dir_path(self) -> Path:
        path = Path(self.GENERATED_CERTIFICATES_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
