import requests, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# Session 90 和 91 的詳細資料
for sid in [90, 91]:
    r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=headers, verify=False)
    if r2.status_code != 200:
        r2 = requests.get(f'{BASE}/api/v1/sessions/{sid}', headers=headers, verify=False)
    print(f'\n=== Session {sid} 詳細 ===')
    import json
    data = r2.json()
    # 只顯示關鍵欄位
    keys = ['session_id','subject_name','created_at','start_time','end_time','total_captures','report_type']
    for k in keys:
        if k in data:
            print(f'  {k}: {data[k]}')

# 取 session 91 所有 captures 中 beta/gamma 分布
print('\n=== Session 91 beta/gamma 分布 ===')
r3 = requests.get(f'{BASE}/api/v1/sessions/91/captures', headers=headers, verify=False)
caps = r3.json().get('captures', [])

beta_100_count = sum(1 for c in caps if c['low_beta'] == 100 or c['high_beta'] == 100)
gamma_100_count = sum(1 for c in caps if c['low_gamma'] == 100 or c['high_gamma'] == 100)
low_eq_high_count = sum(1 for c in caps if c['low_alpha'] == c['high_alpha'])

print(f'總筆數: {len(caps)}')
print(f'beta=100 的筆數: {beta_100_count}')
print(f'gamma=100 的筆數: {gamma_100_count}')
print(f'low_alpha == high_alpha 的筆數: {low_eq_high_count}')

# 前10筆的完整資料
print('\n前5筆：')
for c in caps[:5]:
    print(f"  seq={c['seq_num']:3d} delta={c['delta']:6d} theta={c['theta']:6d} | "
          f"lA={c['low_alpha']:6d} hA={c['high_alpha']:6d} | "
          f"lB={c['low_beta']:6d} hB={c['high_beta']:6d} | "
          f"lG={c['low_gamma']:6d} hG={c['high_gamma']:6d}")
