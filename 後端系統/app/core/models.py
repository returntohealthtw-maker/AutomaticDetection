from sqlalchemy import Column, Integer, Float, String, Text, Enum, ForeignKey, TIMESTAMP, Index, Boolean
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
    # 真正的受測者主檔 FK（核心欄位；舊資料 NULL 表示未關聯，可由 admin 手動指派）
    subject_id       = Column(Integer, ForeignKey("subjects.subject_id", ondelete="SET NULL"), nullable=True, index=True)
    subject_name     = Column(String(50))    # 仍保留 snapshot，但顯示時優先用 subject_id JOIN 結果
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
    # 逐秒原始腦波陣列（JSON 字串）：
    #   { attn:[...180], medi:[...180], r_delta:[...], r_theta:[...],
    #     r_lalpha:[...], r_halpha:[...], r_lbeta:[...], r_hbeta:[...],
    #     r_lgamma:[...], r_hgamma:[...] }
    # 用途：Firebase 補同步 / 未來 MBTI 時間窗重新分析 / 退款爭議舉證
    raw_arrays_json  = Column(Text, nullable=True)
    needs_retest     = Column(Boolean, default=False, nullable=True)  # 管理員標記需重測
    retest_reason    = Column(String(200), nullable=True)             # 標記原因（選填）

    # ── BrainDNA 計算結果（由 braindna_algorithms.compute_all 寫入）──────────
    # 與 Firebase 的欄位名稱、型別、值域完全相同，方便兩庫資料對照
    # mind_stress  : 0-100，壓力分數（MindStressAlgorithm）
    # mind_balance : 0-100，平衡分數（MindBalanceAlgorithm）
    # mind_energy  : 0-100，活力分數（MindEnergyAlgorithm）
    # mind_color   : 0=橙 1=綠 2=藍 3=黃（MindColorAlgorithm）
    # mbti         : 16型字串，如 "INFP"
    # bagua        : 八卦 id，如 "kan"
    # overall_score: 0-100，整體分數（balance×0.6 + energy×0.2 + (100-stress)×0.2）
    mind_stress   = Column(Integer, nullable=True)
    mind_balance  = Column(Integer, nullable=True)
    mind_energy   = Column(Integer, nullable=True)
    mind_color    = Column(Integer, nullable=True)   # 0=橙 1=綠 2=藍 3=黃
    mbti          = Column(String(4), nullable=True)
    bagua         = Column(String(20), nullable=True)
    overall_score = Column(Integer, nullable=True)
    # 演算模式記錄（每個 session 儲存的資料品質標記）：
    # 'bdna_raw'           = BrainDNA 完整演算（原始 ThinkGear 值，最高精度）
    # 'bdna_norm100'       = BrainDNA 降級演算（bandTo100 值做佔比，次高精度）
    # 'fallback_no_raw'    = 無 raw_arrays，使用前端 bandTo100 平均（最低精度）
    # 'fallback_exception' = BrainDNA 例外失敗，使用前端值
    # 'fallback_bdna_invalid_*' = BrainDNA valid=False，使用前端值
    bdna_mode     = Column(String(40), nullable=True)
    # Firebase 同步後取得的 session UUID（供後續從 Firebase 讀取 180 筆特徵用）
    firebase_session_id = Column(String(100), nullable=True)
    # qEEG Z-score 演算結果 JSON（七大能力 + 複合指標 + flags）
    qeeg_scores_json = Column(Text, nullable=True)

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
    # BrainDNA 算術平均 MBTI 專用：bandTo100(arithmetic_mean_raw_lowAlpha/theta)
    mbti_la      = Column(Integer, nullable=True)
    mbti_theta   = Column(Integer, nullable=True)

    session = relationship("Session", back_populates="captures")


class Report(Base):
    """生成的報告"""
    __tablename__ = "reports"

    report_id    = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"), unique=True)
    # 受測者主檔 FK（雙保險：即使 session_id 是 NULL，仍可定位到受測者）
    subject_id   = Column(Integer, ForeignKey("subjects.subject_id", ondelete="SET NULL"), nullable=True, index=True)
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
    error_message = Column(Text, nullable=True)   # 失敗原因（headless 或其他生成錯誤）
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


class Consultant(Base):
    """顧問帳號（加盟商 / 直營商 / 工作人員 ... 以及 admin 管理員）"""
    __tablename__ = "consultants"

    consultant_id   = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(50),  nullable=False)
    phone           = Column(String(20),  nullable=False, unique=True, index=True)  # 登入帳號
    password_hash   = Column(String(128), nullable=False)
    email           = Column(String(120), nullable=True, index=True)
    role            = Column(String(20),  default="consultant")  # consultant / admin
    org_type        = Column(String(50),  nullable=True)   # 加盟商 / 直營商 / 代理商 / 專案人員 / 工作人員 / 其他
    org             = Column(String(100), nullable=True)   # 單位名稱
    is_active       = Column(Integer,     default=1)       # 1=啟用 0=停用
    created_at      = Column(TIMESTAMP,   server_default=func.now())
    updated_at      = Column(TIMESTAMP,   server_default=func.now(), onupdate=func.now())


class ContactRequest(Base):
    """顧問帳號申請（待管理員審核）

    取代原本以 backend/contact_requests.json 儲存的方案。
    放進 DB 後即可在 Railway 重新部署、容器重啟之後仍保留資料。
    """
    __tablename__ = "contact_requests"

    # 沿用前端／舊版產生的 REQxxxxx 字串 ID
    id              = Column(String(40),  primary_key=True)
    name            = Column(String(50),  nullable=False)
    phone           = Column(String(20),  nullable=False, index=True)
    email           = Column(String(120), nullable=False)
    org_type        = Column(String(50),  nullable=True)
    org             = Column(String(100), nullable=True)
    role_label      = Column(String(100), nullable=True)
    ref             = Column(String(100), nullable=True)
    note            = Column(Text,        nullable=True)
    status          = Column(String(20),  default="pending", index=True)  # pending / approved / rejected
    note_admin      = Column(Text,        nullable=True)
    # 核准後產生的顧問帳號 ID。consultants 被刪時不要連帶把申請紀錄刪掉，所以用 SET NULL
    consultant_id   = Column(Integer, ForeignKey("consultants.consultant_id", ondelete="SET NULL"), nullable=True)
    initial_password= Column(String(50),  nullable=True)  # demo 暫存；正式環境應 email 寄出後立即清空
    created_at      = Column(TIMESTAMP,   server_default=func.now())
    handled_at      = Column(TIMESTAMP,   nullable=True)


class ReportGenerationEvent(Base):
    """外部 React App（成人/兒童）回報的「報告生成事件」

    每次「按下生成」會產生一個 correlation_id，整條時間線（章節 1 開始 → 章節 1 完成
    → 章節 2 開始 → ... → PDF 渲染 → GCS 上傳 → 寄信 / 入 queue → 完成）都以同一個
    correlation_id 寫入此表。

    後台「報告生成監看」分頁依 correlation_id 分組，顯示每筆報告的即時進度條 + 錯誤日誌。
    """
    __tablename__ = "report_generation_events"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id  = Column(String(64), nullable=False, index=True)  # UUID（前端生成）
    session_id      = Column(Integer, ForeignKey("sessions.session_id", ondelete="SET NULL"),
                              nullable=True, index=True)
    report_type     = Column(String(20),  default="life_script", index=True)  # life_script/child/parent_child/marital
    variant         = Column(String(20),  default="full")                     # trial/full/vip
    subject_name    = Column(String(50),  nullable=True)
    subject_email   = Column(String(200), nullable=True)
    source          = Column(String(50),  nullable=True)                      # 哪個外部系統
    # 進度 phase：
    #   started / chapter_start / chapter_done / chapter_failed / chapter_retry
    #   pdf_render / gcs_upload / email_sent / queue / done / failed
    phase           = Column(String(30),  nullable=False, index=True)
    chapter_num     = Column(Integer,     nullable=True)   # 1-12
    section_id      = Column(String(10),  nullable=True)   # 如 '1-1', '2-3'
    duration_ms     = Column(Integer,     nullable=True)   # 該步驟耗時
    error_message   = Column(Text,        nullable=True)
    payload_json    = Column(Text,        nullable=True)   # 其他 metadata
    created_at      = Column(TIMESTAMP,   server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_rge_corr_id_ctime", "correlation_id", "created_at"),
        Index("idx_rge_type_ctime",    "report_type", "created_at"),
    )


class Subject(Base):
    """受測者主檔（建檔一次、之後檢測可重複引用）"""
    __tablename__ = "subjects"

    subject_id      = Column(Integer, primary_key=True, autoincrement=True)
    # 由哪位顧問建立。為相容舊資料採用 nullable；正式環境 nullable 的列只有 admin 看得到。
    consultant_id   = Column(Integer, ForeignKey("consultants.consultant_id", ondelete="SET NULL"), nullable=True, index=True)
    name            = Column(String(50),  nullable=False)
    birth_date      = Column(String(10),  nullable=False)  # YYYY-MM-DD
    gender          = Column(String(10),  nullable=False)  # 男 / 女 / 其他
    occupation      = Column(String(50),  nullable=True)   # 職業 / 稱謂
    email           = Column(String(120), nullable=False, index=True)
    phone           = Column(String(20),  nullable=False, index=True)
    medical_history = Column(Text,        nullable=True)
    medications     = Column(Text,        nullable=True)
    created_at      = Column(TIMESTAMP,   server_default=func.now())
    updated_at      = Column(TIMESTAMP,   server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_subject_email_name", "email", "name"),
        Index("idx_subject_consultant", "consultant_id"),
    )


class Payment(Base):
    """付款流水（每次下單 → 第三方付款 → Webhook/Return 都會更新此表）"""
    __tablename__ = "payments"

    payment_id        = Column(Integer, primary_key=True, autoincrement=True)
    order_id          = Column(String(32),  unique=True, nullable=False, index=True)
    # 發起付款的顧問（未登入下單時為 NULL，例如「NT$1 功能測試」可未登入跑）
    consultant_id     = Column(Integer, ForeignKey("consultants.consultant_id", ondelete="SET NULL"), nullable=True, index=True)
    consultant_name   = Column(String(50),  nullable=True)   # snapshot 方便列表不用 join
    subject_name      = Column(String(50),  nullable=True)
    subject_email     = Column(String(200), nullable=True)
    report_type       = Column(String(20),  nullable=False)  # life_trial/life_full/life_vip/child_*/test_1...
    description       = Column(String(100), nullable=True)   # 商品描述（人類可讀）
    amount            = Column(Integer,     nullable=False)
    provider          = Column(String(16),  nullable=False, default="ecpay")  # ecpay/payuni/test/manual
    provider_trade_no = Column(String(64),  nullable=True)   # 第三方訂單號（綠界/PayUni）
    payment_method    = Column(String(32),  nullable=True)   # credit_card/atm/cvs/web_atm/...
    invoice_no        = Column(String(32),  nullable=True)   # 統一發票號碼
    status            = Column(String(16),  nullable=False, default="pending", index=True)
    # pending/paid/failed/expired/refunded
    session_id        = Column(Integer,     nullable=True, index=True)   # 連結到觸發的 session
    created_at        = Column(Integer,     default=0, index=True)
    paid_at           = Column(Integer,     nullable=True)
    expired_at        = Column(Integer,     nullable=True)
    notes             = Column(Text,        nullable=True)   # 失敗原因、退款備註等

    __table_args__ = (
        Index("idx_payment_consultant_status", "consultant_id", "status"),
        Index("idx_payment_ctime", "created_at"),
    )


class ShareRuleSet(Base):
    """分潤規則（全域，按 rule_set_key 區分；目前只用 'default'）"""
    __tablename__ = "share_rule_sets"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    rule_set_key = Column(String(50), unique=True, nullable=False)  # "default"
    rules_json   = Column(Text, nullable=False)   # 整包 JSON
    updated_by   = Column(String(100), nullable=True)
    updated_at   = Column(Integer, default=0)


class FirebaseSyncLog(Base):
    """Firebase 同步佇列 / 日誌

    每筆 session 完成後在此表插入一筆 pending 記錄。
    背景排程定期掃 pending/failed（retry < 5）並嘗試推送 Firebase API。
    已成功推送的記錄保留供稽核，不刪除。

    狀態流：
        pending  → synced  （成功）
        pending  → failed  （失敗，retry_count < MAX_RETRY → 自動重試）
        failed   → synced  （重試成功）
        failed   → failed  （達 MAX_RETRY → 停止重試，需人工處理）
    """
    __tablename__ = "firebase_sync_log"

    id                  = Column(Integer,     primary_key=True, autoincrement=True)
    session_id          = Column(Integer,     ForeignKey("sessions.session_id", ondelete="SET NULL"),
                                              nullable=True, index=True)
    report_id           = Column(Integer,     nullable=True)
    status              = Column(String(16),  default="pending", nullable=False, index=True)
    # pending / syncing / synced / failed
    fb_session_id       = Column(String(128), nullable=True)   # Firebase 端產生的 sessionId
    fb_subject_id       = Column(String(128), nullable=True)   # Firebase 端產生的 subjectId
    retry_count         = Column(Integer,     default=0)
    last_error          = Column(Text,        nullable=True)
    created_at          = Column(TIMESTAMP,   server_default=func.now())
    synced_at           = Column(TIMESTAMP,   nullable=True)
    next_retry_at       = Column(TIMESTAMP,   nullable=True)   # NULL = 立刻可重試

    __table_args__ = (
        Index("idx_fb_sync_status_retry", "status", "next_retry_at"),
    )
