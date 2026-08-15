import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()
screens = re.findall(r'id="(screen-[^"]+)"', content)
print('All screens:')
for s in screens:
    print(f'  {s}')

# find 監控/管理 related text
idx = content.find('監控')
if idx > 0:
    ln = content[:idx].count('\n') + 1
    print(f'\n監控 at line {ln}:')
    print(content[idx-200:idx+400])
