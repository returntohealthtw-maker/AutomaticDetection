import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 age 相關變數/欄位
patterns = ['age', 'Age', '年齡', 'childAge', 'child_age', 'subjectAge', 'years', 'dob']
for p in patterns:
    idx = js.find(p)
    if idx > 0:
        print(f"[{p}] at {idx}: {repr(js[max(0,idx-40):idx+80])}")
        print()

# 找 dw 物件開頭 (整個 dw 結構)
dw_idx = js.find('dw={')
if dw_idx < 0:
    dw_idx = js.find('dw = {')
print(f"\ndw object at: {dw_idx}")

# 找整個生成 prompt 的函式
# 搜尋 "1-1" 前後邏輯
idx_11 = js.find('"1-1"')
print(f"\n\"1-1\" at {idx_11}: {repr(js[idx_11-100:idx_11+200])}")

# 找 subject 的 name/age 在哪裡被用到（report 生成時）
name_pat = js.find('childName')
if name_pat < 0:
    name_pat = js.find('child_name')
print(f"\nchildName at: {name_pat}: {repr(js[max(0,name_pat-20):name_pat+100]) if name_pat>0 else 'not found'}")

# 找 reportData 或 subject 傳入
for kw in ['reportData', 'subject', 'childData', 'child.age', 'child.name', 'parentName', 'parent_name']:
    idx = js.find(kw)
    if idx > 0:
        print(f"\n[{kw}] at {idx}: {repr(js[idx:idx+120])}")
