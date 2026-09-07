"""直接測試對 Firebase 建立一筆 session"""
import requests, json

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
h = {'Authorization': f'Bearer {token}'}

# 先查看 session_id=3 的資料（鄭小怡）
sess_r = requests.get(f'{base}/eeg/sessions?limit=200', headers=h)
sessions = sess_r.json().get('sessions', [])
# 找第一個 firebase_session_id 為空的
no_fb = [s for s in sessions if not s.get('firebase_session_id')]
print(f"沒有 firebase_session_id 的 sessions: {len(no_fb)} 筆")

if no_fb:
    s = no_fb[0]
    print(f"測試 session_id={s['session_id']} {s.get('subject_name')}")

    # 直接測試 Firebase POST
    FB_API = 'https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api'
    FB_KEY = '86pjyXNhJ1PFDEBiIMukV2WxK4QvYZ97qemHLrbG3wngdUfA'
    fh = {'X-Service-Key': FB_KEY, 'Content-Type': 'application/json'}

    payload = {
        'subjectName': s.get('subject_name', '未知'),
        'consultantName': s.get('consultant', '') or s.get('consultant_name', ''),
        'reportType': s.get('report_type', 'life_script'),
        'deviceType': 'android',
        'sessionSource': 'railway_migration',
    }
    print(f"POST payload: {json.dumps(payload, ensure_ascii=False)}")

    fb_r = requests.post(f'{FB_API}/sessions', headers=fh, json=payload)
    print(f"Firebase POST status={fb_r.status_code}")
    print(f"Firebase response: {fb_r.text[:300]}")
