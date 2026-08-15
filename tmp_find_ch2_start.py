import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find the actual dw["2-1"] content start
# It should be after dw["1-4"]
idx = js.find('"2-1":')
print(f"dw['2-1'] at: {idx}")
print("Context:", repr(js[idx:idx+100]))
print()

# Also find end marker
end_idx = js.find('絕對不可以提到任何易經或玄學","3-1"')
print(f"end_idx: {end_idx}")
old_ch2 = js[idx:end_idx + len('絕對不可以提到任何易經或玄學')]
print(f"Total ch2 block length: {len(old_ch2)}")
print("First 200 chars:", repr(old_ch2[:200]))
print()
print("Last 200 chars:", repr(old_ch2[-200:]))
