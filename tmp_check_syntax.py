import sys, subprocess, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 dw["2-2"] 到 dw["2-4"] 的實際字元
idx = js.find('"2-2":')
print(f"dw 2-2 starts at: {idx}")
chunk = js[idx:idx+300]
print("First 300 chars:")
print(repr(chunk))
print()

# 找是否有 "..." 字串中含有真實換行
# 雙引號字串中含 LF = 語法錯誤
dw_2_2 = js.find('"2-2":"')
if dw_2_2 >= 0:
    # 找到下一個 dw key
    next_key = js.find('"2-3":', dw_2_2+5)
    segment = js[dw_2_2:next_key]
    newlines = segment.count('\n')
    print(f"dw['2-2'] segment ({next_key-dw_2_2} chars) contains {newlines} literal newlines")
    if newlines > 0:
        print("  *** BUG: literal newlines inside double-quoted JS string = SyntaxError ***")
        # 找第一個換行的位置
        nl_pos = segment.find('\n')
        print(f"  First newline at relative pos {nl_pos}")
        print(f"  Context: {repr(segment[max(0,nl_pos-30):nl_pos+30])}")

# 同樣檢查 2-3, 2-4
for key in ['"2-3":', '"2-4":']:
    k_idx = js.find(key, dw_2_2)
    if k_idx >= 0:
        next_k = js.find('"3-1"', k_idx) if key == '"2-4":' else js.find('"2-4":', k_idx+5)
        seg = js[k_idx:next_k]
        nls = seg.count('\n')
        print(f"\ndw[{key[:5]}] segment ({next_k-k_idx} chars) contains {nls} literal newlines")
        if nls > 0:
            print(f"  *** BUG ***")
