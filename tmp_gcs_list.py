"""
嘗試列出 GCS bucket 中的舊報告，找回 session 89-98 的舊 PDF URL
"""
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BUCKET = 'brainwave-child-reports'
PREFIX = 'reports/general/'

# 先等 Railway 重啟完成
print("等待 Railway 重啟完成...")
BASE = 'https://backend-production-2da61.up.railway.app'
for i in range(24):
    time.sleep(5)
    try:
        r = requests.post(f'{BASE}/api/v1/auth/login',
                          json={'phone':'0900000000','password':'admin123'}, timeout=8, verify=False)
        if r.status_code == 200:
            print(f"  Railway 已恢復！（{(i+1)*5}秒）")
            break
        print(f"  [{(i+1)*5}s] HTTP {r.status_code}，等待中...")
    except Exception as e:
        print(f"  [{(i+1)*5}s] 連線中... ({type(e).__name__})")
else:
    print("  Railway 未在 2 分鐘內恢復")

# 確認 generating 的 session 都停了
print("\n確認 session 狀態（應全部不再是 generating）...")
r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}
for sid in [98,97,96,95,94,93,92,90,89]:
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
    d = rs.json()
    print(f"  sid={sid} {d.get('subject_name')}: status={d.get('report_status')} url={bool(d.get('report_url'))}")

# 嘗試列出 GCS（無憑證 public 讀取）
print(f"\n嘗試公開讀取 GCS bucket...")
gcs_api = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o?prefix={PREFIX}&maxResults=1000"
try:
    rg = requests.get(gcs_api, timeout=15)
    print(f"GCS list HTTP {rg.status_code}")
    if rg.status_code == 200:
        items = rg.json().get('items', [])
        print(f"共找到 {len(items)} 個檔案")
        # 篩選目標客戶
        targets = ['蔡宛蓉','鄭靜怡','楊女毓','黃映筑']
        for item in items:
            name = item.get('name','')
            for t in targets:
                if t in name:
                    print(f"  {name}")
    else:
        print(f"無法公開讀取：{rg.text[:200]}")
        print("\n需要用 Railway 後端 API 來列出 GCS 檔案")
except Exception as e:
    print(f"GCS list 失敗: {e}")
