from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

_db_url = settings.get_database_url
_engine_kwargs = dict(pool_pre_ping=True, pool_recycle=3600, echo=settings.DEBUG)
if _db_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_db_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI 依賴注入：取得資料庫 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_connection():
    """測試資料庫連線"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"資料庫連線失敗：{e}")
        return False
