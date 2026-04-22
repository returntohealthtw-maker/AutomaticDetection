from sqlalchemy import Column, Integer, Float, String, Text, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# 注意：使用 Integer 以相容 SQLite autoincrement；
# 部署到 MySQL 後，Integer 對應 INT(11)，已足夠儲存 session / capture ID。


class Company(Base):
    """企業／機構名單（後端管理啟用後，前端下拉才可選）"""
    __tablename__ = "companies"

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(100), nullable=False)
    is_active  = Column(Integer, default=1)  # 1=啟用 0=停用
    created_at = Column(Integer, default=0)


class Session(Base):
    """檢測場次"""
    __tablename__ = "sessions"

    session_id       = Column(Integer, primary_key=True, autoincrement=True)
    consultant_name  = Column(String(50), nullable=True)     # 執行檢測的顧問
    subject_name     = Column(String(50))
    subject_birthday = Column(String(10))
    subject_gender   = Column(String(1))
    subject_age      = Column(Integer, default=0)
    company_id       = Column(Integer, ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True)
    report_type      = Column(String(10), default="adult")   # adult / child
    # 企業天賦報告：teacher / student（對應報告範本教師版／學生版）
    report_audience  = Column(String(20), default="student")
    start_time       = Column(Integer, default=0)
    end_time         = Column(Integer, default=0)
    total_captures   = Column(Integer, default=0)
    status           = Column(Integer, default=0)  # 0=進行中 1=成功 2=失敗
    failure_reason   = Column(String(100), nullable=True)
    created_at       = Column(Integer, default=0)

    captures    = relationship("EegCapture", back_populates="session", cascade="all, delete-orphan")
    report      = relationship("Report", back_populates="session", uselist=False)
    company     = relationship("Company")


class EegCapture(Base):
    """腦波原始擷取（每秒一筆）"""
    __tablename__ = "eeg_captures"

    capture_id   = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"))
    seq_num      = Column(Integer, default=0)
    is_baseline  = Column(Integer, default=0)
    captured_at  = Column(Integer, default=0)
    good_signal  = Column(Integer, default=0)
    attention    = Column(Integer, default=0)
    meditation   = Column(Integer, default=0)
    delta        = Column(Integer, default=0)
    theta        = Column(Integer, default=0)
    low_alpha    = Column(Integer, default=0)
    high_alpha   = Column(Integer, default=0)
    low_beta     = Column(Integer, default=0)
    high_beta    = Column(Integer, default=0)
    low_gamma    = Column(Integer, default=0)
    high_gamma   = Column(Integer, default=0)
    feedback     = Column(Integer, default=0)

    session = relationship("Session", back_populates="captures")


class Report(Base):
    """生成的報告"""
    __tablename__ = "reports"

    report_id    = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"), unique=True)
    status       = Column(String(20), default="pending")  # pending/processing/completed/failed
    pdf_url      = Column(Text, nullable=True)
    # 企業專案：客戶掃描用公開頁 token、五段摘要 JSON、Email 通知
    qr_token       = Column(String(64), unique=True, nullable=True, index=True)
    client_summary = Column(Text, nullable=True)  # JSON: 五欄位各約 100 字
    notify_email   = Column(String(200), nullable=True)
    email_sent     = Column(Integer, default=0)
    # 天賦報告版型：child_teacher / child_student / teen_teacher / teen_student
    talent_report_kind = Column(String(32), nullable=True)
    line_sent    = Column(Integer, default=0)
    line_user_id = Column(String(100), nullable=True)
    created_at   = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)

    session      = relationship("Session", back_populates="report")
    indices      = relationship("ReportIndex", back_populates="report", cascade="all, delete-orphan")


class ReportIndex(Base):
    """報告計算結果（30個指標）"""
    __tablename__ = "report_indices"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    report_id    = Column(Integer, ForeignKey("reports.report_id", ondelete="CASCADE"))
    index_name   = Column(String(20))
    index_value  = Column(Float)
    index_pct    = Column(Float)
    category     = Column(String(20))

    report = relationship("Report", back_populates="indices")
