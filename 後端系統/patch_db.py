"""
Patch ALL missing columns in the migrated eeg_dev.db
Based on the full SQLAlchemy model definitions in models.py
"""
import sqlite3

DB = "D:/Write program/Database/ToOtherProject/eeg_dev.db"
conn = sqlite3.connect(DB)

def has_col(table, col):
    try:
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return col in cols
    except Exception:
        return False

patches = [
    # sessions
    ("sessions", "consultant_name",  "ALTER TABLE sessions ADD COLUMN consultant_name VARCHAR(50) NULL"),
    ("sessions", "company_id",       "ALTER TABLE sessions ADD COLUMN company_id INTEGER NULL"),
    ("sessions", "report_audience",  "ALTER TABLE sessions ADD COLUMN report_audience VARCHAR(20) DEFAULT 'student'"),
    # reports
    ("reports",  "subject_id",       "ALTER TABLE reports ADD COLUMN subject_id INTEGER NULL"),
    ("reports",  "consultant_name",  "ALTER TABLE reports ADD COLUMN consultant_name VARCHAR(50) NULL"),
    ("reports",  "qr_token",         "ALTER TABLE reports ADD COLUMN qr_token VARCHAR(64) NULL"),
    ("reports",  "client_summary",   "ALTER TABLE reports ADD COLUMN client_summary TEXT NULL"),
    ("reports",  "notify_email",     "ALTER TABLE reports ADD COLUMN notify_email VARCHAR(200) NULL"),
    ("reports",  "email_sent",       "ALTER TABLE reports ADD COLUMN email_sent INTEGER DEFAULT 0"),
    ("reports",  "talent_report_kind","ALTER TABLE reports ADD COLUMN talent_report_kind VARCHAR(32) NULL"),
]

for table, col, sql in patches:
    if not has_col(table, col):
        conn.execute(sql)
        conn.commit()
        print(f"  ADDED  {table}.{col}")
    else:
        print(f"  OK     {table}.{col}")

# Also check eeg_captures for any new columns
eeg_cols = [c[1] for c in conn.execute("PRAGMA table_info(eeg_captures)").fetchall()]
print(f"\neeg_captures columns ({len(eeg_cols)}): {eeg_cols}")

# Check subjects
subj_cols = [c[1] for c in conn.execute("PRAGMA table_info(subjects)").fetchall()]
print(f"subjects columns ({len(subj_cols)}): {subj_cols}")

conn.close()
print("\nPatch complete.")
