import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HTML = r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html'
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# 找 admin console 的主 tab bar
idx_console = html.find('screen-admin-console')
console_area = html[idx_console:idx_console+3000]
print("=== admin-console start ===")
print(console_area[:2000])

print("\n=== Looking for pane navigation ===")
# 找 showPane 或 showAdminPane 等 function
pane_calls = re.findall(r'showPane\([\'"](admin-pane-[^\'"]+)[\'"]\)', html[:80000])
print("showPane calls:", set(pane_calls))

# 找 tab bar text
idx_tab_bar = html.find('admin-tab-bar')
if idx_tab_bar < 0:
    idx_tab_bar = html.find('tab-bar')
print(f"\ntab-bar at {idx_tab_bar}: {html[idx_tab_bar:idx_tab_bar+500]}")

# 找 admin-pane-monitor 前面的 tab label
idx_monitor_pane = html.find('id="admin-pane-monitor"')
ctx_before = html[max(0, idx_monitor_pane-2000):idx_monitor_pane]
print("\n=== Context before admin-pane-monitor ===")
print(ctx_before[-500:])
