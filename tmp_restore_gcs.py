"""
從 GCS 找回舊報告 URL 並寫回 DB
"""
import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE    = 'https://backend-production-2da61.up.railway.app'
BUCKET  = 'brainwave-child-reports'
PREFIX  = 'reports/general/'

# 登入
r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}

# 目標 session 及客戶名
TARGETS = [
    (98, '蔡宛蓉'), (97, '鄭靜怡'), (96, '楊女毓'),
    (95, '鄭靜怡'), (94, '鄭靜怡'), (93, '楊女毓'),
    (92, '鄭靜怡'), (90, '黃映筑'), (89, '楊女毓'),
]

# 嘗試公開讀取 GCS（不驗 SSL）
print("嘗試列出 GCS bucket...")
gcs_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o?prefix={PREFIX}&maxResults=1000"
try:
    rg = requests.get(gcs_url, timeout=20, verify=False)
    print(f"GCS HTTP {rg.status_code}")
    if rg.status_code == 200:
        items = rg.json().get('items', [])
        print(f"共 {len(items)} 個檔案\n")

        # 為每個 session 找最近的舊報告（排除今天生成的）
        import datetime
        today_prefix = datetime.date.today().strftime('%Y')  # 用年份過濾不夠精確，改用時間戳
        # 今天 2026-07-21 00:00 UTC+8 = 1784563200 秒 = 1784563200000 毫秒
        TODAY_MS = 1784563200000

        results = {}
        for item in items:
            obj_name = item.get('name', '')
            # 提取時間戳（格式：reports/general/1784611735733_名字_...）
            try:
                ts_str = obj_name.split('/')[2].split('_')[0]
                ts_ms = int(ts_str)
            except:
                continue

            # 只考慮今天以前的（排除今天的重新生成）
            if ts_ms >= TODAY_MS:
                continue

            base_url = f"https://storage.googleapis.com/{BUCKET}/{obj_name}"
            # 比對客戶名
            for sid, name in TARGETS:
                if name in obj_name:
                    if sid not in results or ts_ms > results[sid]['ts']:
                        results[sid] = {'name': name, 'url': base_url, 'ts': ts_ms, 'obj': obj_name}

        print("找到的舊報告：")
        for sid, info in sorted(results.items()):
            print(f"  sid={sid} {info['name']}: {info['obj']}")

        # 寫回 DB（透過 Railway 後端的 signed-url 或直接 patch report）
        print("\n嘗試用 Railway admin endpoint 寫回 pdf_url...")
        # 嘗試用 PATCH /api/v1/monitor/sessions/{sid}/report 等方式
        # 或用 /api/v1/reports/record callback 格式
        for sid, info in sorted(results.items()):
            # 嘗試透過 /reports/record (callback endpoint) 寫入
            payload = {
                "session_id": sid,
                "pdf_url":    info['url'],
                "status":     "completed",
            }
            for ep in [
                f'/api/v1/reports/record',
                f'/api/v1/reports/sessions/{sid}/restore',
                f'/api/v1/monitor/sessions/{sid}/restore-report',
            ]:
                try:
                    rr = requests.post(f'{BASE}{ep}', headers=H, json=payload, timeout=10, verify=False)
                    if rr.status_code in [200, 204]:
                        print(f"  ✅ sid={sid} {info['name']}: 寫回成功 via {ep}")
                        break
                    elif rr.status_code != 404:
                        print(f"  sid={sid} {ep}: HTTP {rr.status_code} {rr.text[:80]}")
                except Exception as e:
                    pass
            else:
                print(f"  ⚠️  sid={sid} {info['name']}: 沒有可用的 endpoint，需要新增")

    elif rg.status_code == 401 or rg.status_code == 403:
        print("GCS bucket 不允許公開讀取，需要使用服務帳號憑證")
        print("請在 Railway Variables 中找到 GCP_SERVICE_ACCOUNT_JSON 並提供給我")
    else:
        print(f"GCS list 失敗: {rg.text[:300]}")

except Exception as e:
    print(f"GCS 連線失敗: {e}")
    print("\n改走替代方案：用 Railway backend 的 signed-url endpoint 嘗試復原...")
