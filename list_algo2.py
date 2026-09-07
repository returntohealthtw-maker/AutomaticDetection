import os, sys
sys.stdout.reconfigure(encoding='utf-8')
algo_dir = 'D:/Write program/AutomaticDetection/相關資料/演算法'
for root, dirs, files in os.walk(algo_dir):
    level = root.replace(algo_dir, '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}[{os.path.basename(root)}]')
    for f in sorted(files):
        print(f'{indent}  {f}')
