import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('D:/Write program/Database/ToOtherProject/eeg_dev.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])

# Also check prod DB path hint
import os
for candidate in [
    'D:/Write program/Database/ToOtherProject/eeg_dev.db',
    'eeg_dev.db',
]:
    if os.path.exists(candidate):
        c2 = sqlite3.connect(candidate)
        tbls = [t[0] for t in c2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f'{candidate}: {tbls}')
