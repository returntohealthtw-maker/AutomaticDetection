"""觸發全部 Session 重新計算 BrainDNA（使用新的 30K 過濾）"""
import sys, urllib3, requests
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 批次重算
print('觸發批次重新計算...')
resp = requests.post(f'{BASE}/api/admin/recompute-braindna', headers=hdrs, verify=False, timeout=120)
print(f'狀態: {resp.status_code}')
try:
    data = resp.json()
    print(f'結果: {data}')
except:
    print(f'回應: {resp.text[:500]}')

# 看 Session 60 最新的 stats
print()
print('[驗證 Session #60 最新 stats]')
resp2 = requests.get(f'{BASE}/api/v1/eeg/sessions/60/stats', headers=hdrs, verify=False, timeout=30)
if resp2.ok:
    d = resp2.json()
    bands = d.get('bands', d.get('bands_avg', {}))
    print(f"  high_beta={bands.get('high_beta','?')}  low_gamma={bands.get('low_gamma','?')}")
    print(f"  全部頻段: {bands}")
