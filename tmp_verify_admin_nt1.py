"""驗證 admin NT$1 測試模式的程式邏輯是否正確落地"""
import requests, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'

# 1. 確認後端版本已更新
r = requests.get(f'{BASE}/health', verify=False, timeout=10)
print(f'Health: {r.status_code}')

r2 = requests.get(f'{BASE}/api/v1/app/version', verify=False, timeout=10)
vj = r2.json()
print(f'HTML version: {vj.get("html_version")}')

# 2. 確認 app_prototype.html 已包含新程式碼（搜尋關鍵字）
import re
r3 = requests.get(f'{BASE}/static-app/app_prototype.html', verify=False, timeout=30)
html = r3.text
if '_adminNt1Test' in html:
    print('[OK] _adminNt1Test 邏輯已在線上 HTML 中')
else:
    print('[FAIL] 線上 HTML 尚未包含 _adminNt1Test 邏輯')

# 確認關鍵字都存在
checks = [
    ('_adminNt1Test', '_adminNt1Test 常數'),
    ('Admin NT$1', '[Admin NT$1] 標題'),
    ('qrScreen = \'screen-qr-test\'', 'qrScreen 覆蓋'),
    ("_adminNt1Test ? 1 :", '金額覆蓋為 1'),
]
for keyword, desc in checks:
    found = keyword in html
    print(f'  {"OK" if found else "FAIL"} - {desc}')

print('\n驗證完成')
