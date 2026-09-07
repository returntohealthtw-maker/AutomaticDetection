import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import rarfile

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'
dst = 'D:/Write program/AutomaticDetection/相關資料/_extracted/BrainDNA'
os.makedirs(dst, exist_ok=True)

with rarfile.RarFile(rar_path) as rf:
    names = rf.namelist()
    print(f'Total files: {len(names)}')
    for n in names[:60]:
        print(n)
    if len(names) > 60:
        print(f'... and {len(names)-60} more')
