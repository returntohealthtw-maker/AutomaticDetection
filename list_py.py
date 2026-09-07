import sys, os, io, rarfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

with rarfile.RarFile(rar_path) as rf:
    names = rf.namelist()
    print(f'Total files: {len(names)}')
    py_files = [n for n in names if n.endswith('.py')]
    print(f'Python files: {len(py_files)}')
    for f in py_files:
        print(f'  {f}')
