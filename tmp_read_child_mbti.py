import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check which child JS file is the main one
import os
files = [
    r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js',
    r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-C2_ayCDM.js',
]
for f in files:
    size = os.path.getsize(f)
    print(f"{os.path.basename(f)}: {size:,} bytes")

# Read the larger one
main_js_path = max(files, key=os.path.getsize)
print(f"\nReading: {os.path.basename(main_js_path)}")

with open(main_js_path, 'r', encoding='utf-8') as f:
    js = f.read()
print(f"Total chars: {len(js):,}")

# Find MBTI-related functions
for fn in ['function wu(', 'function Ux(', 'mbti', 'MBTI', '2-1', 'chapter.*2']:
    idx = js.find(fn)
    if idx >= 0:
        print(f"\n=== {fn!r} at {idx} ===")
        print(js[idx:idx+500])

# Find chapter 2 prompt
idx2 = js.find('"2-1"')
if idx2 >= 0:
    print(f"\n=== Child ch2 prompts ===")
    print(js[idx2:idx2+3000])
