import requests, urllib3, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'
ver = requests.get(BASE+'/api/v1/app/version', verify=False, timeout=10).json()
print('version=', ver.get('html_version'))
# 確認線上 HTML 已含 save-stats 修復
html = requests.get(BASE+'/static-app/app_prototype.html', verify=False, timeout=30).text
checks = [
    ('緊急修復 2026-07-30', '緊急修復 2026-07-30' in html),
    ('save-stats 路徑', "/eeg/save-stats" in html),
    ('不再 firebase-only 主路徑', 'Firebase-Only 儲存成功' not in html),
    ('AndroidBridge 判斷', 'typeof AndroidBridge' in html and 'typeof Android !==' not in html.split('function _persistEegStats')[1][:800] if 'function _persistEegStats' in html else False),
]
for name, ok in checks:
    print(('OK' if ok else 'FAIL'), name)
# 再確認 _persistEegStats 區段
idx = html.find('function _persistEegStats')
snippet = html[idx:idx+900]
print('--- _persistEegStats 片段 ---')
print(snippet[:700])
