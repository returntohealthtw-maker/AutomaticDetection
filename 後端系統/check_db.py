import sqlite3
conn = sqlite3.connect("D:/Write program/Database/ToOtherProject/eeg_dev.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for tbl in tables:
    n = tbl[0]
    cols = conn.execute(f"PRAGMA table_info({n})").fetchall()
    count = conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]
    print(f"  {n}: {count} rows, cols={[c[1] for c in cols]}")
conn.close()
