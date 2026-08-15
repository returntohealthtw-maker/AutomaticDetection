import os, sys
sys.stdout.reconfigure(encoding='utf-8')
base = 'D:/Write program/AutomaticDetection'
for d in sorted(os.listdir(base)):
    full = os.path.join(base, d)
    if os.path.isdir(full):
        try:
            subs = os.listdir(full)
            print(f'[{d}]')
            for sub in sorted(subs)[:20]:
                print(f'  {sub}')
        except Exception as e:
            print(f'[{d}] ERROR: {e}')
