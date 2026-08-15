import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()

# Find apiFetch function to understand what it does
idx = content.find('function apiFetch')
ln = content[:idx].count('\n') + 1
print(f'apiFetch at line {ln}:')
print(content[idx:idx+600])
