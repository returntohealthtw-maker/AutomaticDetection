"""
資料庫搬移腳本：
  1. 用 SQLite backup API 安全複製（確保資料一致性）
  2. 驗證目標 DB 資料完整
"""
import sqlite3, os, sys

SRC  = r"D:\Write program\AutomaticDetection\後端系統\eeg_dev.db"
DST  = r"D:\Write program\Database\ToOtherProject\eeg_dev.db"

print(f"來源: {SRC}")
print(f"目標: {DST}")
print()

# 1. 使用 SQLite backup API（類似熱備份，確保一致性）
src_conn = sqlite3.connect(SRC)
dst_conn = sqlite3.connect(DST)
src_conn.backup(dst_conn)
dst_conn.close()
src_conn.close()
print("OK backup done")

# 2. 驗證目標 DB
src_conn = sqlite3.connect(SRC)
dst_conn = sqlite3.connect(DST)

src_cur = src_conn.cursor()
dst_cur = dst_conn.cursor()

src_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in src_cur.fetchall()]

print(f"\n驗證 {len(tables)} 張資料表：")
all_ok = True
for t in tables:
    src_n = src_conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    dst_n = dst_conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    ok = "✅" if src_n == dst_n else "❌"
    if src_n != dst_n:
        all_ok = False
    print(f"  {ok} {t:40s} {src_n:>6d} rows → {dst_n:>6d} rows")

src_conn.close()
dst_conn.close()

print()
src_size = os.path.getsize(SRC)
dst_size = os.path.getsize(DST)
print(f"來源大小: {src_size:,} bytes")
print(f"目標大小: {dst_size:,} bytes")

if all_ok:
    print("\n✅ 所有資料完整複製成功！")
else:
    print("\n❌ 資料筆數不符，請重新確認！")
    sys.exit(1)
