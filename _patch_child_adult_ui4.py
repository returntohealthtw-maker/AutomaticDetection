"""
修正 A6 check - d97706 的驗證應用 # 前綴
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 重新驗證所有 patches
checks = [
    ('Av object', 'const Av='),
    ('Ad object', 'const Ad=['),
    ('$u adult_child', 'xinReportType==="adult_child")return Ad'),
    ('ip prompt Av', 'd==="adult_child"?Av[c]'),
    ('ip role adult', '高階成人心理分析師'),
    ('age>=18 G(adult)', 'if(_a>=18)G("adult")'),
    ('Le adult_child', 'ne==="adult"?{...se,xinReportType:"adult_child"}'),
    ('grid-cols-3', 'grid-cols-1 sm:grid-cols-3'),
    ('adult button onClick', 'onClick:()=>G("adult")'),
    ('adult color #d97706', '#d97706'),
    ('adult 18歲 text', '"18 歲以上"'),
]
all_ok = True
for name, marker in checks:
    found = marker in js
    print(f"  {'✓' if found else '✗'} {name}")
    if not found:
        all_ok = False
        
print(f"\n{'All checks passed!' if all_ok else 'Some checks FAILED'}")

# 確認 A6b 的狀態，如果 adult button 存在但沒有 #d97706，重新應用
if 'onClick:()=>G("adult")' in js and '#d97706' not in js:
    print("\nAdult button exists but color missing, checking...")
    idx = js.find('onClick:()=>G("adult")')
    print(repr(js[max(0,idx-20):idx+200]))
elif 'onClick:()=>G("adult")' not in js:
    print("\nAdult button missing, re-applying...")
    # 重新應用 A6b
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
        print("[OK] Adult button re-applied")
        with open(JS_PATH, 'w', encoding='utf-8') as f:
            f.write(js)
    else:
        print("[FAIL] Cannot find teen button end for re-apply")
        idx = js.find('"約 13～18 歲"')
        print(repr(js[idx:idx+100]))
else:
    print("\nAll patches confirmed present. File is good.")
