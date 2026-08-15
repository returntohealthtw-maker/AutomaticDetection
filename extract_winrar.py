import sys, os, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

src = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'
dst = 'D:/Write program/AutomaticDetection/相關資料/_extracted/BrainDNA'
os.makedirs(dst, exist_ok=True)

# Try WinRAR unrar.exe
for exe in [
    r'C:\Program Files\WinRAR\unrar.exe',
    r'C:\Program Files (x86)\WinRAR\unrar.exe',
    'unrar',
]:
    if os.path.isfile(exe) or exe == 'unrar':
        try:
            r = subprocess.run(
                [exe, 'x', '-y', src, dst + '\\'],
                capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace'
            )
            print(f'Exit: {r.returncode}')
            print(r.stdout[-500:] if r.stdout else '')
            print(r.stderr[-300:] if r.stderr else '')
            break
        except Exception as e:
            print(f'{exe}: {e}')

# Check result
extracted = 'D:/Write program/AutomaticDetection/相關資料/_extracted/BrainDNA'
if os.path.exists(extracted):
    for root, dirs, files in os.walk(extracted):
        level = root.replace(extracted, '').count(os.sep)
        if level < 3:
            indent = ' ' * level
            print(f'{indent}{os.path.basename(root)}/')
            if level >= 2:
                for f in files[:5]:
                    print(f'{indent}  {f}')
