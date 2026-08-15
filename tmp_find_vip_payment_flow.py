import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()

# Find createPaymentOrder calls and context
idxs = [m.start() for m in re.finditer(r'createPaymentOrder\(', content)]
for idx in idxs:
    ln = content[:idx].count('\n') + 1
    print(f'Line {ln}:')
    print(content[max(0,idx-200):idx+300])
    print('---')

# Also find where screen-qr-vip is triggered
idx2 = content.find('screen-qr-vip')
ln2 = content[:idx2].count('\n') + 1
print(f'\nscreen-qr-vip first ref at line {ln2}:')
print(content[max(0,idx2-200):idx2+400])
