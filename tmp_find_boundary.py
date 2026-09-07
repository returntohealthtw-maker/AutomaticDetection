import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 2-1 開始
s = js.find('"2-1":`【MBTI v6.0 主副性格完整分析】')
print(f"START: {s}")
if s < 0:
    # 舊的 2-1 格式？
    s2 = js.find('"2-1":')
    print(f'Fallback "2-1": {s2}')
    chunk = js[s2:s2+200]
    print(f"Content: {repr(chunk)}")
    exit()

# 找 2-4 那段
idx_24 = js.find('"2-4":', s)
print(f'"2-4" at: {idx_24}')
chunk_24 = js[idx_24:idx_24+100]
print(f"2-4 start: {repr(chunk_24)}")

# 找 2-4 後第一個 , 或 } 來判斷結束
# 往後找 3-1 或 } 或 ,"
end_candidates = []
for marker in ['"3-1"', ',"3-', '},"', "},Ws"]:
    idx = js.find(marker, idx_24+5)
    if idx > 0:
        end_candidates.append((idx, marker))
end_candidates.sort()
print(f"\nEnd candidates: {end_candidates[:5]}")

# 顯示 2-4 末尾
if end_candidates:
    e_idx = end_candidates[0][0]
    print(f"\nLast 200 chars of ch2 block:")
    print(repr(js[e_idx-200:e_idx+20]))
