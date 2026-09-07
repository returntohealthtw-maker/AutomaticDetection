import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找兒童報告 dw ch2 區塊
s = js.find('"2-1":')
if s < 0:
    print("No 2-1 found")
    exit()
chunk = js[s:s+200]
print(f'"2-1" at {s}: {repr(chunk)}')

# 找 2-2, 2-3, 2-4
for key in ['"2-2":', '"2-3":', '"2-4":']:
    idx = js.find(key, s)
    if idx < 0:
        print(f"{key} not found")
        continue
    seg_start = idx
    # 找下一個 key 作為 end
    next_keys = ['"2-3":', '"2-4":', '"3-1":', ',"3-']
    next_idx = len(js)
    for nk in next_keys:
        ni = js.find(nk, seg_start + 10)
        if 0 < ni < next_idx:
            next_idx = ni
    seg = js[seg_start:next_idx]
    nls = seg.count('\n')
    print(f"{key} segment ({next_idx-seg_start} chars): {nls} literal newlines {'*** BUG ***' if nls else 'OK'}")
    if nls > 0:
        print(f"  First 100: {repr(seg[:100])}")
