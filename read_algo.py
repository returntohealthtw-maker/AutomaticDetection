import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import rarfile

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

key_files = [
    'BrainDNA-master (核心檔案)/braindna/algorithms/MBTIPersonality.py',
    'BrainDNA-master (核心檔案)/braindna/algorithms/bagua.py',
    'BrainDNA-master (核心檔案)/braindna/algorithms/brainwave.py',
]

with rarfile.RarFile(rar_path) as rf:
    for fname in key_files:
        print('='*70)
        print(f'FILE: {fname}')
        print('='*70)
        try:
            content = rf.read(fname).decode('utf-8', errors='replace')
            print(content)
        except Exception as e:
            print(f'ERROR: {e}')
        print()
