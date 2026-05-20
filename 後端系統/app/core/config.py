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

    # 金流共用：切換目前用哪一家（ecpay / payuni）
    PAYMENT_PROVIDER: str = "payuni"

    # 綠界金流 ECPay（舊版相容；若 PAYMENT_PROVIDER=ecpay 才會用）
    ECPAY_MERCHANT_ID: str = ""
    ECPAY_HASH_KEY:    str = ""
    ECPAY_HASH_IV:     str = ""
    ECPAY_TEST_MODE:   bool = True

    # PayUni 統一金流（正式）
    # 後台索取：MerchantID / HashKey / HashIV
    PAYUNI_MER_ID:     str = ""
    PAYUNI_HASH_KEY:   str = ""      # 長度通常 32
    PAYUNI_HASH_IV:    str = ""      # 長度通常 16
    PAYUNI_TEST_MODE:  bool = False  # True 用 sandbox，False 走正式環境
    # 對外可被使用者開的回呼網址（Railway 公開網址）
    PUBLIC_BASE_URL:   str = ""      # e.g. https://backend-production-xxxx.up.railway.app

    # AI 報告生成（Gemini）
    GEMINI_API_KEY:       str = ""
    GEMINI_TEXT_MODEL:    str = "gemini-2.5-pro"        # 章節內文生成
    GEMINI_EXTRACT_MODEL: str = "gemini-2.5-flash"      # OCR / 簡單任務
    GEMINI_IMAGE_MODEL:   str = "gemini-2.5-flash-image"  # 插圖生成

    # 報告模板（私有 GitHub repo）
    GITHUB_PAT: str = ""   # Personal Access Token，能讀私有 BrianaveReportImage repo

    # ──────────── 外部報告系統 (Orchestrator 呼叫) ────────────
    # 預設指向已部署的 4 個系統；要換成自訂網址用 Railway env vars 覆蓋
    REPORT_URL_LIFE_SCRIPT:  str = "https://brianave-report-image.vercel.app"
    REPORT_URL_CHILD:        str = "https://brianwave-child.vercel.app"
    REPORT_URL_PARENT_CHILD: str = "https://web-production-f1aec.up.railway.app"
    REPORT_URL_MARITAL:      str = "https://web-production-2c7d43.up.railway.app"
    REPORT_REQUEST_TIMEOUT_SEC: int = 900  # 外部生成最多等 15 分鐘

    # Gmail SMTP（寄送 AI 生成後的報告 email 給受測者）
    GMAIL_USER:         str = ""   # your.account@gmail.com
    GMAIL_APP_PASSWORD: str = ""   # 16 字元 App Password（不是 Gmail 密碼）
    GMAIL_FROM_NAME:    str = "onlineReport 線上腦波分析系統"

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
