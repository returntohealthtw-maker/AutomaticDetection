import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False

# 1. 確認版本已部署
r = s.get(f'{BASE}/api/v1/app/version')
v = r.json()
print(f"部署版本: html_version={v.get('html_version')} (期望: 2026.06.29.05)")
if v.get('html_version') != '2026.06.29.05':
    print("⚠️  版本未更新，Railway 可能尚未部署完成")
    sys.exit(1)
print("✅ 版本確認")

# 2. 登入
r2 = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r2.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 3. 呼叫 retrigger-qeeg for session 89
print("\n=== 重新計算 session 89 的 qEEG ===")
r3 = s.get(f'{BASE}/debug/retrigger-qeeg/89')
if r3.status_code != 200:
    print(f"❌ 失敗: {r3.status_code} {r3.text[:500]}")
    sys.exit(1)
result = r3.json()
print(json.dumps(result, ensure_ascii=False, indent=2))
