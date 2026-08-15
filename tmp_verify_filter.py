"""驗證過濾後 Session #60 的結果"""
import sys, urllib3, requests
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 呼叫 compare-windows 端點（它會重新執行 BrainDNA 算法）
resp = requests.get(f'{BASE}/api/admin/compare-windows/60', headers=hdrs, verify=False, timeout=30)
data = resp.json()
print('[Session #60 重新計算結果（已加入過濾）]')
if 'window_30s' in data:
    w = data['window_30s']
    print(f"  delta={w.get('delta')}  theta={w.get('theta')}")
    print(f"  low_alpha={w.get('low_alpha')}  high_alpha={w.get('high_alpha')}")
    print(f"  low_beta={w.get('low_beta')}  high_beta={w.get('high_beta')}")
    print(f"  low_gamma={w.get('low_gamma')}  high_gamma={w.get('high_gamma')}")
else:
    print(f"  回應: {data}")

# 也觸發 recompute 儲存
resp2 = requests.post(f'{BASE}/api/admin/recompute-braindna/60', headers=hdrs, verify=False, timeout=60)
print(f'\n[觸發重新計算並儲存] → {resp2.status_code}: {resp2.text[:200]}')
