import sys, os, io, rarfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

with rarfile.RarFile(rar_path) as rf:
    names = rf.namelist()
    py_files = [n for n in names if n.endswith('.py')]
    
    for fname in py_files:
        try:
            content = rf.read(fname).decode('utf-8', errors='replace')
            if 'calculateMBTIGroup' in content or 'personality' in content.lower():
                lines = content.split('\n')
                hits = [(i+1, l) for i, l in enumerate(lines) 
                        if 'calculateMBTIGroup' in l or 'personality' in l.lower() 
                        or 'points' in l or 'MBTI' in l]
                if hits:
                    short = fname.split('/')[-1]
                    print(f'\n=== {short} ===')
                    for lineno, l in hits[:20]:
                        print(f'  {lineno}: {l}')
        except Exception as e:
            pass
