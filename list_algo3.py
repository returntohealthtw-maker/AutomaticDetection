import os, sys
sys.stdout.reconfigure(encoding='utf-8')
out = 'D:/Write program/AutomaticDetection/相關資料/_extracted/BrainDNA'
for root, dirs, files in os.walk(out):
    level = root.replace(out, '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}[{os.path.basename(root)}]')
    for f in sorted(files):
        size = os.path.getsize(os.path.join(root, f))
        print(f'{indent}  {f}  ({size} bytes)')
