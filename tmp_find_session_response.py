import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\app\routers\eeg.py', encoding='utf-8').read()
idx = content.find('def list_my_sessions')
if idx < 0:
    idx = content.find('/eeg/sessions')
print(f'list_my_sessions at char {idx}')
ln = content[:idx].count('\n') + 1
print(f'Line {ln}')
print(content[idx:idx+2500])
