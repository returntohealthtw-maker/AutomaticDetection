import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找 _regenerateSessionReport 的完整實作
idx = html.find('_regenerateSessionReport')
print(f"_regenerateSessionReport at {idx}")
print(html[max(0,idx-20):idx+1000])

print("\n\n=== 報告管理 pane 的報告列表渲染 ===")
idx_reports = html.find('id="admin-pane-reports"')
print(html[idx_reports:idx_reports+2000])
