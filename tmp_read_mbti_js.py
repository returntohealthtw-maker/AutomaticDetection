import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Find the Ux() function (MBTI axis calculation - original)
idx = js.find('function Ux(')
print("=== Ux() function (MBTI axis calc) ===")
print(js[idx:idx+2000])
print()

# 2. Find wu() function (MBTI type + secondaries)
idx2 = js.find('function wu(')
print("=== wu() function (MBTI main) ===")
print(js[idx2:idx2+3000])
print()
