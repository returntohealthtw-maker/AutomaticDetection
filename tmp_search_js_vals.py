import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

js_path = r"D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js"
with open(js_path, encoding='utf-8', errors='replace') as f:
    js = f.read()

print(f"JS 檔案大小: {len(js):,} 字元\n")

# 找 focus / relaxation 在 BrainDNA context 中的使用
print("=== 搜尋 focus / relaxation 相關 ===")
# 找 maxArray 或 bandTo100 附近的 focus/relaxation
for pat in [r'focus', r'relaxation', r'attention', r'meditation']:
    positions = [m.start() for m in re.finditer(pat, js)]
    print(f"'{pat}' 出現次數: {len(positions)}")
    for pos in positions[:5]:
        snippet = js[max(0,pos-60):pos+80]
        print(f"  ...{snippet}...")
    print()

# 找報告中顯示 放鬆/專注 的地方
print("=== 搜尋 放鬆/專注 顯示邏輯 ===")
for pat in [r'放鬆', r'專注']:
    positions = [m.start() for m in re.finditer(pat, js)]
    print(f"'{pat}' 出現: {len(positions)} 次")
    for pos in positions[:3]:
        snippet = js[max(0,pos-100):pos+100]
        print(f"  ...{snippet}...")
    print()
