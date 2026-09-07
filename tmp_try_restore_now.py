import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE   = 'https://backend-production-2da61.up.railway.app'
BUCKET = 'brainwave-child-reports'

r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}

# 測試端點
rt = requests.post(f'{BASE}/api/v1/monitor/sessions/98/restore-pdf-url',
                   headers=H, json={'pdf_url': 'test'}, timeout=10, verify=False)
print(f"端點測試: HTTP {rt.status_code} → {rt.text[:100]}")

OLD_URLS = {
    89: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    90: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782789742499_黃映筑_成人腦波報告.pdf",
    92: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    93: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    94: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    95: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    96: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    97: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    98: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782967365745_蔡宛蓉_成人腦波報告.pdf",
}
NAMES = {89:'楊女毓',90:'黃映筑',92:'鄭靜怡',93:'楊女毓',94:'鄭靜怡',
         95:'鄭靜怡',96:'楊女毓',97:'鄭靜怡',98:'蔡宛蓉'}

if rt.status_code == 200:
    print("\n端點已上線，開始還原...")
    for sid, url in sorted(OLD_URLS.items()):
        rr = requests.post(f'{BASE}/api/v1/monitor/sessions/{sid}/restore-pdf-url',
                           headers=H, json={'pdf_url': url}, timeout=15, verify=False)
        print(f"  {'✅' if rr.status_code==200 else '❌'} sid={sid} {NAMES[sid]}: HTTP {rr.status_code}")

    print("\n確認結果：")
    for sid in sorted(OLD_URLS.keys()):
        rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
        d = rs.json()
        print(f"  sid={sid} {NAMES[sid]}: status={d.get('report_status')} url={bool(d.get('report_url'))}")
else:
    print("\n端點尚未部署，請稍後再試")
