import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

js_path = r"D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js"
with open(js_path, encoding='utf-8', errors='replace') as f:
    js = f.read()

# 搜尋 qeeg_ 相關欄位
print("=== qeeg_ 欄位搜尋 ===")
matches = list(re.finditer(r'qeeg_\w+', js))
qeeg_fields = set(m.group() for m in matches)
print(f"所有 qeeg_ 欄位: {sorted(qeeg_fields)}\n")

for field in sorted(qeeg_fields):
    positions = [m.start() for m in re.finditer(re.escape(field), js)]
    print(f"'{field}' ({len(positions)} 次):")
    for p in positions[:3]:
        print(f"  {js[max(0,p-80):p+100]}")
    print()

# 搜尋 bar chart 顯示值的地方（放鬆/focus 值在 chart 中）
print("=== 搜尋 bar chart 值渲染 ===")
for kw in ['qeeg_focus', 'qeeg_attention', 'qeeg_relaxation', 'qeeg_meditation']:
    pos = js.find(kw)
    if pos >= 0:
        print(f"[{kw}]")
        print(js[max(0,pos-200):pos+200])
        print()
