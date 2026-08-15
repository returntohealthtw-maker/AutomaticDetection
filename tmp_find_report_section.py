import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找親子選項的更大範圍
idx = html.find('parent_child')
print("=== parent_child context (±500) ===")
print(html[max(0,idx-500):idx+500])

print("\n=== tab 列表 ===")
# 找所有的 tab 名稱
import re
tabs = re.findall(r'(?:tab|Tab|分頁)[^"\'<>]*["\']([^"\'<>]+)["\']', html[:5000])
for t in tabs[:20]:
    print(f"  {t}")

# 找主 tab 選單
tab_start = html.find('<nav') 
if tab_start < 0:
    tab_start = html.find('tab-nav')
print(f"\nnav at {tab_start}: {html[tab_start:tab_start+500]}")
