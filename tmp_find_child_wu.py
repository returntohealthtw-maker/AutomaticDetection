import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js', 'r', encoding='utf-8') as f:
    cjs = f.read()

# Find bw() function - the child equivalent of adult wu()
idx = cjs.find('function bw(')
print(f"bw() at {idx}:")
print(repr(cjs[idx:idx+800]))
print()

# Also check if child has mbti_primary server-side shortcut
idx2 = cjs.find('mbti_primary')
print(f"mbti_primary in child: {idx2 >= 0}")
if idx2 >= 0:
    print(repr(cjs[idx2-100:idx2+100]))
print()

# Find child dw["2-1"] to ["2-4"] exact block
start = cjs.find('"2-1":"【MBTI 腦波演算法】')
end_marker = '並提供一個讓自己快速回到最好狀態的小秘訣"'
end = cjs.find(end_marker) + len(end_marker)
print(f"Child ch2 block: [{start} : {end}]")
print(f"Length: {end - start}")
print("First 100:", repr(cjs[start:start+100]))
print("Last 100:", repr(cjs[end-100:end]))
