import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import rarfile

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

with rarfile.RarFile(rar_path) as rf:
    names = rf.namelist()
    # Find files that USE calculateMBTIGroup or personalityGroups
    target_files = [n for n in names if n.endswith('.py') and 'test' not in n.lower() 
                    and 'migration' not in n.lower()]
    
    # Read all Python files and search for MBTI group usage
    for fname in target_files:
        try:
            content = rf.read(fname).decode('utf-8', errors='replace')
            if 'calculateMBTIGroup' in content or 'personalityGroups' in content or 'MBTI' in content:
                print(f'\n=== {fname} ===')
                # Print relevant lines
                for i, line in enumerate(content.split('\n')):
                    if any(kw in line for kw in ['calculateMBTI', 'personalityGroup', 'MBTI', 'personality', 'points']):
                        print(f'  {i+1}: {line}')
        except:
            pass
