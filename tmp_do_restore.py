"""等 Railway 部署完成後，把 9 個 session 的舊 GCS URL 寫回 DB"""
import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE   = 'https://backend-production-2da61.up.railway.app'
BUCKET = 'brainwave-child-reports'

# 已從 GCS 找到的舊報告對應
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

# 等待 Railway 部署完成（新 endpoint 上線）
print("等待 Railway 部署新版本（含 restore-pdf-url endpoint）...")
for i in range(36):
    time.sleep(5)
    try:
        r0 = requests.post(f'{BASE}/api/v1/auth/login',
                           json={'phone':'0900000000','password':'admin123'}, timeout=8, verify=False)
        if r0.status_code != 200:
            print(f"  [{(i+1)*5}s] 登入失敗 {r0.status_code}")
            continue
        tok = r0.json()['token']
        H = {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}
        # 測試新 endpoint 是否存在（用 session 98 試）
        rt = requests.post(f'{BASE}/api/v1/monitor/sessions/98/restore-pdf-url',
                           headers=H, json={'pdf_url': 'test'}, timeout=8, verify=False)
        if rt.status_code in [200, 400, 422]:
            print(f"  ✅ 新 endpoint 已上線（{(i+1)*5}秒）")
            break
        elif rt.status_code == 404:
            print(f"  [{(i+1)*5}s] 尚未部署...")
        else:
            print(f"  [{(i+1)*5}s] HTTP {rt.status_code}")
    except Exception as e:
        print(f"  [{(i+1)*5}s] 連線中...")

# 執行還原
print("\n=== 還原舊 GCS URL 到 DB ===")
r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}

for sid, url in sorted(OLD_URLS.items()):
    rr = requests.post(f'{BASE}/api/v1/monitor/sessions/{sid}/restore-pdf-url',
                       headers=H, json={'pdf_url': url}, timeout=15, verify=False)
    if rr.status_code == 200:
        print(f"  ✅ sid={sid} {NAMES[sid]}: 已還原")
    else:
        print(f"  ❌ sid={sid} {NAMES[sid]}: HTTP {rr.status_code} {rr.text[:80]}")

# 確認結果
print("\n=== 確認還原結果 ===")
for sid in sorted(OLD_URLS.keys()):
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
    d = rs.json()
    print(f"  sid={sid} {NAMES[sid]}: status={d.get('report_status')} url={bool(d.get('report_url'))}")
