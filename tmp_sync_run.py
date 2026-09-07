"""
步驟 1：同步 86 筆缺少 firebase_session_id 的 sessions 到 Firebase
步驟 2：重跑付款同步（背景等 2 分鐘後執行）
"""
import requests, time, json

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
h = {'Authorization': f'Bearer {token}'}

print("== 步驟 1：觸發 sync-sessions-to-firebase（背景執行）==")
r = requests.post(f'{base}/admin/sync-sessions-to-firebase', headers=h, params={'dry_run': 'false'})
print(f'status={r.status_code}')
print(r.json())

print("\n== 等待 3 分鐘讓背景同步完成... ==")
for i in range(18):
    time.sleep(10)
    print(f"  已等待 {(i+1)*10} 秒...")

print("\n== 步驟 2：檢查有多少 sessions 已獲得 firebase_session_id ==")
# 再次 dry-run 確認剩餘數量
r2 = requests.post(f'{base}/admin/sync-sessions-to-firebase', headers=h, params={'dry_run': 'true'})
data2 = r2.json()
remaining = len(data2.get('sessions', []))
print(f'剩餘沒有 firebase_session_id: {remaining} 筆')
if remaining == 0:
    print('全部同步完成！')
else:
    print(data2.get('message'))
