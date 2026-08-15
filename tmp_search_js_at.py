import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

js_path = r"D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js"
with open(js_path, encoding='utf-8', errors='replace') as f:
    js = f.read()

# 找 At= 物件的完整定義（資料提取 mapping）
pos = js.find('At={focus:et(["attention_percentage"')
if pos == -1:
    pos = js.find('At={focus:et(')
if pos >= 0:
    print("=== At 物件（資料欄位 mapping）===")
    print(js[max(0,pos-20):pos+800])
    print()

# 找 et 函式定義
print("=== et() 函式定義 ===")
matches = list(re.finditer(r'function et\(', js))
if not matches:
    # 可能是 const et= 形式
    matches = list(re.finditer(r'(?:const|let|var)\s+et\s*=\s*', js))
for m in matches[:2]:
    print(js[m.start():m.start()+300])
    print()

# 找 Ye 函式定義
print("=== Ye() 函式定義（fallback 預設值）===")
matches_ye = list(re.finditer(r'function Ye\(', js))
if not matches_ye:
    matches_ye = list(re.finditer(r'(?:const|let|var)\s+Ye\s*=\s*', js))
for m in matches_ye[:2]:
    print(js[m.start():m.start()+300])
    print()

# 找報告資料怎麼傳入 bar chart 的
print("=== 搜尋 bandTo100 / brainwave_data 傳入 ===")
for keyword in ['bandData', 'brainData', 'eegData', 'scoreData', 'wu(', 'wu ']:
    positions = [m.start() for m in re.finditer(re.escape(keyword), js)]
    if positions:
        print(f"'{keyword}': {len(positions)} 次")
        for p in positions[:2]:
            print(f"  {js[max(0,p-50):p+150]}")
        print()
