import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找 child-report 相關的入口
for kw in ['child-report', 'childReport', '親子', 'parent-child', 'child_report']:
    idx = html.find(kw)
    if idx > 0:
        print(f"[{kw}] at {idx}: {html[max(0,idx-100):idx+200]}")
        print()

# 找報告生成的 URL
for kw in ['report-app', 'child-report-app', '/report', 'generateReport', 'gen_report']:
    idx = html.find(kw)
    if idx > 0:
        print(f"[{kw}] at {idx}: {html[max(0,idx-60):idx+150]}")
        print()
