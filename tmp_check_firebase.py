"""透過 Railway 後端測試 Firebase metadata PATCH（Railway 有 service key）"""
import requests

base = 'https://backend-production-2da61.up.railway.app/api/v1'
pg_token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
ph = {'Authorization': f'Bearer {pg_token}'}

# 打一個 Railway monitor 端點，它內部用 service key 呼叫 Firebase
# 先找 session 104 的 firebase_session_id
s104 = requests.get(f'{base}/eeg/sessions/104/stats', headers=ph).json()
fb_sid = s104.get('firebase_session_id','')
print(f'fb_sid: {fb_sid}')

# 用 Railway 後端呼叫 Firebase（Railway 有 service key）
# 建立一個臨時測試端點
r = requests.post(f'{base}/monitor/test-firebase-patch', headers=ph, json={
    'firebase_session_id': fb_sid,
    'payload': {'metadata': {'testField': 'hello'}}
})
print(f'Railway→Firebase PATCH test: {r.status_code} {r.text[:300]}')
