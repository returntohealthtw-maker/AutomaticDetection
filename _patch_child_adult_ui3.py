"""
加入「成人（18+）」UI 按鈕 - 最終版
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# PATCH A6a: grid-cols-2 → grid-cols-3
old_grid = 'className:"grid grid-cols-1 sm:grid-cols-2",style:{gap:"12px"}'
new_grid = 'className:"grid grid-cols-1 sm:grid-cols-3",style:{gap:"12px"}'
if old_grid in js:
    js = js.replace(old_grid, new_grid, 1)
    print("[OK] A6a: grid-cols-2 → grid-cols-3")
else:
    print("[FAIL] A6a: grid target not found")

# PATCH A6b: 在 teen 按鈕後加成人按鈕
# 找到 teen 按鈕的結束
old_teen_end = (
    'children:"約 13～18 歲"})]})]})]}),M.jsxs("div",{className:"bg-white border border-slate-100 shadow-sm"'
)
new_teen_end = (
    'children:"約 13～18 歲"})]})'
    ',M.jsxs("button",{type:"button",onClick:()=>G("adult"),style:{padding:"16px 18px",borderRadius:"16px",'
    'border:ne==="adult"?"2px solid #d97706":"2px solid #e2e8f0",'
    'background:ne==="adult"?"#fffbeb":"white",'
    'boxShadow:ne==="adult"?"0 4px 16px rgba(217,119,6,0.2)":"none",'
    'cursor:"pointer",textAlign:"left"},'
    'children:['
    'M.jsx("p",{className:"font-black",style:{fontSize:"15px",color:ne==="adult"?"#b45309":"#1e293b",marginBottom:"4px"},children:"成人版報告"}),'
    'M.jsx("p",{className:"font-medium text-slate-500",style:{fontSize:"11px",marginBottom:"8px"},children:"親子動力 · 原生家庭 · 自我探索"}),'
    'M.jsx("span",{style:{display:"inline-block",background:ne==="adult"?"#d97706":"#f1f5f9",color:ne==="adult"?"white":"#64748b",fontSize:"10px",padding:"2px 10px",borderRadius:"6px",fontWeight:900},children:"18 歲以上"})'
    ']})'
    ']})]}),M.jsxs("div",{className:"bg-white border border-slate-100 shadow-sm"'
)
if old_teen_end in js:
    js = js.replace(old_teen_end, new_teen_end, 1)
    print("[OK] A6b: adult button added")
else:
    print("[FAIL] A6b: teen button end not found")
    # debug
    idx = js.find('"約 13～18 歲"')
    print(f"  Teen age text at {idx}: {repr(js[idx:idx+50])}")

# 驗證
checks = [
    ('grid-cols-3', 'grid-cols-1 sm:grid-cols-3'),
    ('adult button', 'onClick:()=>G("adult")'),
    ('adult border amber', '"d97706"'),
    ('adult text 18歲', '"18 歲以上"'),
]
all_ok = True
for name, marker in checks:
    found = marker in js
    print(f"  {'✓' if found else '✗'} {name}")
    if not found:
        all_ok = False

if all_ok:
    with open(JS_PATH, 'w', encoding='utf-8') as f:
        f.write(js)
    print(f"\n[OK] Written to {JS_PATH}")
else:
    print("[ABORT] Some checks failed")
