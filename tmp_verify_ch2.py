import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. 找所有包含 "主性格" 的章節標題定義
print("=== 所有 '主性格' 出現在 title 附近的位置 ===")
import re
for m in re.finditer(r'title:"[^"]*主性格[^"]*"', js):
    print(f"  pos={m.start()}: {m.group()}")

print()

# 2. 找 Ws 陣列裡的 ch2
print("=== Ws 陣列中 第2章 subs 內容 ===")
ws_idx = js.find('"主性格 × 性格動力學"')
if ws_idx >= 0:
    print(f"  [OK] 找到新標題 at pos={ws_idx}")
    print("  Content:", repr(js[ws_idx:ws_idx+200]))
else:
    print("  [MISSING] 新標題 '主性格 × 性格動力學' 不存在！")

old_idx = js.find('"主性格 × 腦波運作"')
if old_idx >= 0:
    print(f"  [WARN] 舊標題 '主性格 × 腦波運作' 仍存在 at pos={old_idx}")
    print("  Content:", repr(js[old_idx:old_idx+200]))
else:
    print("  [OK] 舊標題已不存在")

print()

# 3. 找 Ws 這個變數的定義位置，看整個 ch2 結構
print("=== Ws 變數定義 ===")
ws_def = js.find('const Ws=[')
if ws_def >= 0:
    print(f"  found at {ws_def}")
    print(repr(js[ws_def:ws_def+600]))
else:
    print("  not found as 'const Ws=['")
    # 找其他定義方式
    alt = js.find('Ws=[{title:')
    print(f"  alt search 'Ws=[{{title:': {alt}")
    if alt >= 0:
        print(repr(js[alt:alt+400]))

print()

# 4. 找 dw["2-1"] 的當前內容
print("=== dw['2-1'] 當前內容前100字 ===")
dw_idx = js.find('"2-1":`【MBTI v6.0 主副性格')
if dw_idx >= 0:
    print(f"  [OK] 新prompt已存在 at pos={dw_idx}")
else:
    print("  [MISSING] 新2-1 prompt 不存在")
    # 找舊的
    old_dw = js.find('"2-1":`【腦波性格地圖')
    old_dw2 = js.find('"2-1":`【MBTI v6.0 主性格 × 四軸強度解析】')
    print(f"  舊prompt '腦波性格地圖': {old_dw}")
    print(f"  v6.0第1版prompt: {old_dw2}")
    if old_dw2 >= 0:
        print(repr(js[old_dw2:old_dw2+100]))

# 5. 找報告前端用的 HTML index.html
print()
print("=== index.html 的 script 引用 ===")
import os
html_path = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
print(html[:1000])
