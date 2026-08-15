import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# age URL param 完整上下文
idx = js.find('"age"]=parseInt')
# 往前找 function 開頭
ctx_start = max(0, idx - 600)
ctx_end = min(len(js), idx + 600)
print("=== age URL param context ===")
print(repr(js[ctx_start:ctx_end]))

print("\n" + "="*60)

# ne 狀態的設定
idx_ne_set = js.find(',ne=gt.useState(')
if idx_ne_set < 0:
    idx_ne_set = js.find('ne=gt.useState(')
print(f"\nne useState at {idx_ne_set}: {repr(js[idx_ne_set:idx_ne_set+200])}")

# 找 ne 被賦值的地方（setNe 或 類似）
idx_ne_child = js.find('ne==="child"')
print(f"\nAll 'ne' state updates around ne==='child' context:")
print(repr(js[max(0,idx_ne_child-500):idx_ne_child+100]))

# 找 pe=gt.useState（xinReportType 狀態）
idx_pe = js.find(',pe=gt.useState(')
print(f"\npe useState at {idx_pe}: {repr(js[idx_pe:idx_pe+200])}")
