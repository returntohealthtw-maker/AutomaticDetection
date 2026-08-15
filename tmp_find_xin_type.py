import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. 找 xinReportType 所有出現
print("=== xinReportType occurrences ===")
start = 0
while True:
    idx = js.find('xinReportType', start)
    if idx < 0:
        break
    print(f"  at {idx}: {repr(js[max(0,idx-60):idx+80])}")
    start = idx + 1

# 2. 找 ac= 或 const ac= 定義
print("\n=== ac variable search ===")
for pat in ['const ac=', 'let ac=', 'var ac=', ',ac={', ';ac={']:
    idx = js.find(pat)
    if idx > 0:
        print(f"[{pat}] at {idx}: {repr(js[idx:idx+200])}")
        break

# 3. 找 vw= （可能是 ac 的別名）
print("\n=== vw variable ===")
for pat in ['const vw=', 'vw={', ',vw=']:
    idx = js.find(pat)
    if idx > 0:
        print(f"[{pat}] at {idx}: {repr(js[idx:idx+200])}")

# 4. 找 subject_age 或 age 欄位
print("\n=== age field in data ===")
for pat in ['subject_age', 'age:', '"age"', 'childAge']:
    start = 0
    count = 0
    while count < 3:
        idx = js.find(pat, start)
        if idx < 0:
            break
        print(f"[{pat}] at {idx}: {repr(js[max(0,idx-30):idx+80])}")
        start = idx + 1
        count += 1
