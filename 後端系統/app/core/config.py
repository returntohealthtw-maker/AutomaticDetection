from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Railway 直接注入 DATABASE_URL（最優先）
    DATABASE_URL: Optional[str] = None

    # MySQL（GCP 備用）
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "eeg_system"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    GCS_BUCKET_NAME: str = ""
    GCS_PROJECT_ID: str = ""

    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""

    SECRET_KEY: str = "dev-secret-key"
    DEBUG: bool = True
    REPORT_BASE_URL: str = "http://localhost:8000/reports"

    USE_SQLITE: bool = False

    # 綠界金流 ECPay
    ECPAY_MERCHANT_ID: str = ""
    ECPAY_HASH_KEY:    str = ""
    ECPAY_HASH_IV:     str = ""
    ECPAY_TEST_MODE:   bool = True   # True = 測試環境，False = 正式環境

    @property
    def get_database_url(self) -> str:
        # 1. Railway / 任何環境注入的 DATABASE_URL
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        # 2. 本地 SQLite
        if self.USE_SQLITE:
            return "sqlite:///./eeg_dev.db"
        # 3. GCP MySQL
        return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                f"?charset=utf8mb4")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
