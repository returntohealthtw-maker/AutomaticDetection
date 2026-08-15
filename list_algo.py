import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
algo_dir = 'D:/Write program/AutomaticDetection/相關資料/演算法'
for item in os.listdir(algo_dir):
    path = os.path.join(algo_dir, item)
    size = os.path.getsize(path) if os.path.isfile(path) else '-'
    print(f'{item}  ({size} bytes)')
    if os.path.isdir(path):
        for sub in os.listdir(path):
            print(f'  {sub}')
