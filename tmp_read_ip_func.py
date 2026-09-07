import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# ip 函式從 852194 開始，讀 800 chars
print("=== ip function (852194 - 853200) ===")
print(repr(js[852194:853200]))

print("\n=== ip function (853200 - 854200) ===")
print(repr(js[853200:854200]))
