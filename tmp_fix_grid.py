import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 找到 grid 並確認
idx = js.find('grid grid-cols-1 sm:grid-cols-2')
print(f"grid-cols-2 at {idx}: {repr(js[max(0,idx-20):idx+100])}")

old_grid = '"grid grid-cols-1 sm:grid-cols-2",style:{gap:"12px"}'
new_grid = '"grid grid-cols-1 sm:grid-cols-3",style:{gap:"10px"}'

if old_grid in js:
    js = js.replace(old_grid, new_grid, 1)
    print("[OK] grid-cols-2 → grid-cols-3")
    with open(JS_PATH, 'w', encoding='utf-8') as f:
        f.write(js)
    print("Written")
else:
    # 找所有 grid-cols 相關
    pos = 0
    while True:
        p = js.find('grid-cols', pos)
        if p < 0:
            break
        print(f"  grid-cols at {p}: {repr(js[p:p+60])}")
        pos = p + 1
