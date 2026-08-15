import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find ch2 section prompts (dw object - section algorithm descriptions)
# We already saw dw starts with "1-1", find the 2-x entries
idx = js.find('"2-1"')
print("=== Chapter 2 prompts (dw object) ===")
# Extract everything from "2-1" to end of chapter 2 prompts
chunk = js[idx:idx+4000]
print(chunk[:4000])
print()

# Find Ux() + Px() + jx() + Ix() + zx() - MBTI sub-functions
for fn in ['function Ox(', 'function Px(', 'function jx(', 'function Ix(', 'function zx(']:
    i2 = js.find(fn)
    if i2 >= 0:
        print(f"=== {fn} ===")
        print(js[i2:i2+800])
        print()
