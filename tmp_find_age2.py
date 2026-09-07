import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# age URL param 在 1629534
idx = 1629534
print("=== age URL param context (wider) ===")
print(repr(js[idx-200:idx+800]))

print("\n" + "="*60)
# 找 ne 用法
idx_ne = js.rfind(',ne,', 0, 1640000)
print(f"\nne destructure at {idx_ne}: {repr(js[max(0,idx_ne-100):idx_ne+300])}")

# 找所有 useState 的使用（找到主要 component 的 state）
# 在 ne==="child" 前找最近的 useState 群組
idx_ne2 = js.find('ne==="child"')
# 在這之前 2000 chars 裡找 useState
chunk = js[max(0,idx_ne2-3000):idx_ne2]
usestate_positions = []
pos = 0
while True:
    p = chunk.find('useState(', pos)
    if p < 0:
        break
    usestate_positions.append(p)
    pos = p + 1
print(f"\nuseState calls in 3000 chars before ne==child: {len(usestate_positions)}")
# 最後幾個
for p in usestate_positions[-5:]:
    abs_p = max(0,idx_ne2-3000) + p
    print(f"  at {abs_p}: {repr(js[abs_p-20:abs_p+80])}")

# 找 "child" 字串的賦值
print("\n=== 'child' string assignments ===")
start = 0
count = 0
while count < 10:
    idx = js.find('"child"', start)
    if idx < 0:
        break
    ctx = js[max(0,idx-30):idx+80]
    if '=' in ctx[:30] or 'State' in ctx or 'useState' in ctx:
        print(f"  at {idx}: {repr(ctx)}")
        count += 1
    start = idx + 1
