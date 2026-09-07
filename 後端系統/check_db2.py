import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('D:/Write program/Database/ToOtherProject/eeg_dev.db')
conn.row_factory = sqlite3.Row
# Check sessions table columns
cols = conn.execute("PRAGMA table_info(sessions)").fetchall()
print("sessions columns:", [c['name'] for c in cols])
cols2 = conn.execute("PRAGMA table_info(eeg_captures)").fetchall()
print("eeg_captures columns:", [c['name'] for c in cols2])
