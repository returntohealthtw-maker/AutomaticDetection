import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import rarfile

rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'

with rarfile.RarFile(rar_path) as rf:
    names = rf.namelist()
    # Focus on algorithm Python files
    algo_files = [n for n in names if n.endswith('.py') and 'algorithm' in n.lower()]
    print('Algorithm Python files:')
    for n in algo_files:
        print(' ', n)
    
    print()
    # All Python files in braindna/algorithms/
    core_files = [n for n in names if '/algorithms/' in n and n.endswith('.py')]
    print('Core algorithm files:')
    for n in core_files:
        print(' ', n)
    
    print()
    # Also look for MBTI-related files
    mbti_files = [n for n in names if 'mbti' in n.lower() or 'personality' in n.lower() or 'bagua' in n.lower()]
    print('MBTI/personality/bagua files:')
    for n in mbti_files:
        print(' ', n)
