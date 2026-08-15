import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 teen_student 那段 switch/case
idx = js.find('"teen_student"')
print(f"teen_student at {idx}")
print("Context (-300 to +200):")
print(repr(js[max(0,idx-300):idx+200]))
print()

# 找 R6 是什麼
r6_idx = js.rfind('R6=', 0, idx)  # 往前找 R6= 定義
print(f"\nR6= at {r6_idx}")
print(repr(js[r6_idx:r6_idx+500]))

# 找 ac= 定義（default case）
ac_idx = js.rfind(',ac=', 0, idx)
print(f"\nac= at {ac_idx}")
print(repr(js[ac_idx:ac_idx+200]))

# 找整個 switch 結構
switch_start = js.rfind('switch', 0, idx)
print(f"\nswitch at {switch_start}: {repr(js[switch_start:switch_start+400])}")
