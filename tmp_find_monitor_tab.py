import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找 monitor 所在的 tab section
idx_mon = html.find('monitor-filter-type')
# 往前找 tab section id
tab_ctx = html[max(0,idx_mon-3000):idx_mon]
# 找最後一個 id="xxx-tab" 或 data-tab
tab_ids = list(re.finditer(r'id="([^"]+)"', tab_ctx))
print("=== Last 5 IDs before monitor filter ===")
for m in tab_ids[-5:]:
    print(f"  {m.group(1)}")

# 找主導航標籤文字
print("\n=== Navigation tabs (button text) ===")
nav_btns = re.findall(r'<button[^>]*onclick=["\'][^"\']*["\'][^>]*>([^<]+)</button>', html[:20000])
for b in nav_btns[:20]:
    print(f"  {b.strip()}")

# 找所有的 section id / div id 定義 (tab containers)  
section_ids = [(m.start(), m.group(1)) for m in re.finditer(r'<(?:div|section)[^>]*\bid="([^"]+)"', html)]
print("\n=== Section IDs (first 30) ===")
for pos, sid in section_ids[:30]:
    print(f"  {sid} at {pos}")

# 找 tab button 的所有 text
tab_buttons = re.findall(r'onclick="[^"]*tab[^"]*"\s*[^>]*>([^<]+)<', html[:20000], re.IGNORECASE)
print("\n=== Tab buttons ===")
for t in tab_buttons[:20]:
    print(f"  {t.strip()}")
