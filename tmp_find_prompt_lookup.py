import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 vw 怎麼被引用 (vw[, vw.)
print("=== vw usages ===")
start = 688000  # after vw definition
count = 0
while count < 8:
    idx = js.find('vw[', start)
    if idx < 0:
        break
    print(f"  at {idx}: {repr(js[max(0,idx-80):idx+100])}")
    start = idx + 1
    count += 1

# 找 prompt 用在哪個 function
print("\n=== prompt generation function ===")
# 找包含 vw 和 prompt 的函式
idx_prompt = js.find('vw[a]')
if idx_prompt < 0:
    idx_prompt = js.find('vw[e]')
if idx_prompt < 0:
    idx_prompt = js.find('vw[i]')
print(f"vw[x] at {idx_prompt}: {repr(js[max(0,idx_prompt-200):idx_prompt+200])}")

# 找 "prompt" 的使用
print("\n=== 'prompt' usages ===")
start = 850000
count = 0
while count < 5:
    idx = js.find('"prompt"', start)
    if idx < 0:
        break
    print(f"  at {idx}: {repr(js[max(0,idx-50):idx+150])}")
    start = idx + 1
    count += 1

# ne 的 UI 顯示  
print("\n=== ne button UI (child/teen/adult) ===")
idx_btn = js.find('onClick:()=>G("child")')
print(f"child btn at {idx_btn}: {repr(js[max(0,idx_btn-100):idx_btn+400])}")
