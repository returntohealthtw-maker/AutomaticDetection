import sys, os, io, rarfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

key_files = [
    'BrainDNA-master (核心檔案)/braindna/apps/distributor/evaluationReport.py',
    'BrainDNA-master (核心檔案)/braindna/apps/distributor/reports.py',
]

with rarfile.RarFile(rar_path) as rf:
    for fname in key_files:
        try:
            content = rf.read(fname).decode('utf-8', errors='replace')
            short = fname.split('/')[-1]
            print(f'\n{"="*70}')
            print(f'FILE: {short}')
            print('='*70)
            print(content)
        except Exception as e:
            print(f'Error reading {fname}: {e}')
