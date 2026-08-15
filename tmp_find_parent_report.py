import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 "孩子真實面貌" 出現在哪
idx = js.find('孩子真實面貌')
print(f"'孩子真實面貌' at {idx}")
print(repr(js[max(0,idx-200):idx+200]))

print("\n" + "="*60)

# 找 institution 相關的 report 結構
# 找所有的 institution 值
for val in ['"general"', '"parent"', '"family"', '"親子"']:
    idx = js.find(val)
    if idx > 0:
        print(f"\n{val} at {idx}: {repr(js[max(0,idx-40):idx+120])}")

# 找子女報告的章節定義（用年齡判斷的那段）
idx_ne = js.find('ne==="child"')
print(f"\nne===\"child\" at {idx_ne}: {repr(js[max(0,idx_ne-200):idx_ne+400])}")

# 找一般親子報告的 dw（prompts）
idx_dw = js.find('dw["1-1"]')
if idx_dw < 0:
    idx_dw = js.find("dw[\"1-1\"]")
print(f"\ndw['1-1'] at: {idx_dw}")

# 找 dw 物件建立的地方
idx_dw2 = js.find('dw={}')
if idx_dw2 < 0:
    idx_dw2 = js.find('let dw')
    if idx_dw2 < 0:
        idx_dw2 = js.find('const dw')
print(f"\ndw object creation at: {idx_dw2}")
if idx_dw2 > 0:
    print(repr(js[idx_dw2:idx_dw2+300]))
