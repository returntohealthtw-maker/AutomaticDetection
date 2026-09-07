import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find exact start of "2-1" in dw object and end of "2-4"
start = js.find('"2-1":"【腦波性格地圖')
print(f"Adult dw 2-1 start: {start}")
print("START context:", repr(js[start:start+50]))
print()

# Find "3-1" that follows "2-4"
end_marker = '絕對不可以提到任何易經或玄學","3-1"'
end = js.find(end_marker)
print(f"Adult dw 2-4 end: {end}")
print("END context:", repr(js[end:end+100]))
print()

# Check wu() fallback code exact string
wu_fallback = 'const r=Ux({highAlpha:a.highAlpha,lowAlpha:a.lowAlpha,highBeta:a.highBeta,lowBeta:a.lowBeta,lowGamma:a.lowGamma,highGamma:a.highGamma,theta:a.theta,focus:a.focus,relaxation:a.relaxation}),[e,i]=F5[r.mbti]'
idx = js.find(wu_fallback)
print(f"wu() fallback found: {idx >= 0}")
print("FALLBACK context:", repr(js[idx:idx+50]))
print()

# Find adult chapter 2 titles in Ws array
ws_ch2 = '"主性格 × 腦波運作"'
idx2 = js.find(ws_ch2)
print(f"Adult Ws ch2: {idx2}")
print("WS context:", repr(js[idx2:idx2+150]))
print()

# Check child JS for similar boundaries
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js', 'r', encoding='utf-8') as f:
    cjs = f.read()

# Find child ch2 dw content
cstart = cjs.find('"2-1":"【MBTI 腦波演算法】')
print(f"Child dw 2-1 start: {cstart}")
# Find end of child "2-4"
c2_4_end = cjs.find(',"3-1"')
# Find the last "2-4" before "3-1"
c2_4 = cjs.rfind('"2-4"', 0, c2_4_end)
print(f"Child dw 2-4 start: {c2_4}")
print("Child 2-4 end (before 3-1):", repr(cjs[c2_4_end-50:c2_4_end+20]))
print()

# Find child MBTI calculation (the E/I axis formula)
child_ei = cjs.find('(γ↑+專注力)÷2 vs (α↓+放鬆度)÷2')
print(f"Child 2-1 MBTI formula found: {child_ei >= 0}")

# Find child wu or MBTI function  
child_mbti_fn = cjs.find('mbti:s,mbtiEn:P5')
print(f"Child MBTI calc at: {child_mbti_fn}")
print("Child MBTI context:", repr(cjs[max(0,child_mbti_fn-300):child_mbti_fn+100]))
