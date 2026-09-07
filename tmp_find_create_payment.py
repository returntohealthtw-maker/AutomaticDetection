import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()

# Find all calls to /payments/create
idxs = [m.start() for m in re.finditer(r'payments/create|createPayment\b', content)]
for idx in idxs:
    ln = content[:idx].count('\n') + 1
    print(f'Line {ln}:')
    print(content[max(0,idx-300):idx+400])
    print('---')
