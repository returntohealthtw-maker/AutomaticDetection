from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MySQL（GCP）
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "eeg_system"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Railway PostgreSQL（優先使用）
    DATABASE_URL_OVERRIDE: Optional[str] = None   # Railway 自動注入 DATABASE_URL

    GCS_BUCKET_NAME: str = ""
    GCS_PROJECT_ID: str = ""

    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""

    SECRET_KEY: str = "dev-secret-key"
    DEBUG: bool = True
    REPORT_BASE_URL: str = "http://localhost:8000/reports"

    USE_SQLITE: bool = False  # 本地開發用 SQLite

    # 統一金流 PAYUNi
    PAYUNI_MERCHANT: str = ""
    PAYUNI_HASH_KEY: str = ""
    PAYUNI_HASH_IV:  str = ""

    @property
    def DATABASE_URL(self) -> str:
        # 1. Railway 環境：使用 DATABASE_URL_OVERRIDE（即 Railway 的 DATABASE_URL）
        if self.DATABASE_URL_OVERRIDE:
            url = self.DATABASE_URL_OVERRIDE
            # Railway PostgreSQL URL 格式為 postgres://，SQLAlchemy 需要 postgresql://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        # 2. 本地開發：SQLite
        if self.USE_SQLITE:
            return "sqlite:///./eeg_dev.db"
        # 3. GCP MySQL
        return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                f"?charset=utf8mb4")

    class Config:
        env_file = ".env"
        # 允許 Railway 注入的 DATABASE_URL 環境變數對應到 DATABASE_URL_OVERRIDE
        env_prefix = ""

settings = Settings(_env_file=".env", DATABASE_URL_OVERRIDE=None)

# 嘗試讀取 Railway 注入的 DATABASE_URL
import os
_railway_db = os.environ.get("DATABASE_URL")
if _railway_db:
    settings.DATABASE_URL_OVERRIDE = _railway_db
