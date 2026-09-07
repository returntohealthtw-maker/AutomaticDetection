import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找主要 tab 按鈕/標籤
# 找 onclick="switchTab" 或類似
tab_clicks = [(m.start(), m.group()) for m in re.finditer(r'switchTab\([^\)]+\)', html)]
print("=== Tab switch calls ===")
for pos, match in tab_clicks[:20]:
    ctx = html[max(0,pos-50):pos+100]
    print(f"  {match}: {ctx.strip()[:100]}")

# 找 renderAdminMonitor 的功能描述
idx_mon = html.find('renderAdminMonitor')
print(f"\n=== renderAdminMonitor context ===")
print(html[max(0,idx_mon-200):idx_mon+400])

# 找重新生成報告的按鈕
for kw in ['重新生成', '重生成', 'regenerate', 'reGenerate', '再次生成']:
    idx = html.find(kw)
    if idx > 0:
        print(f"\n[{kw}] at {idx}: {html[max(0,idx-80):idx+200]}")
