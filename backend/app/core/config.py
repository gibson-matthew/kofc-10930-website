from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List, Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Council Management API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Security / Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    # CORS_ORIGINS: List[AnyHttpUrl] = []
    CORS_ORIGINS: List[str] = ["*"]

    # Email
    EMAIL_FROM: str
    EMAIL_SERVER: str
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_TLS: bool = True

    # Media
    MEDIA_UPLOAD_DIR: str = "app/media/uploads"
    MEDIA_THUMBNAIL_DIR: str = "app/media/thumbnails"

    # Background tasks / Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()

