import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()
idx = content.find('screen-admin-console')
ln = content[:idx].count('\n') + 1
print(f'screen-admin-console at line {ln}')
print(content[idx:idx+4000])
