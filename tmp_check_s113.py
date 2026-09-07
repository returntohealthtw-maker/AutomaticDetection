"""Simulate _bw_from_session for session #113 and check attention"""
import requests, json, urllib3
urllib3.disable_warnings()

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False).json()['token']
h = {'Authorization': f'Bearer {token}'}

# 查全部 captures
rc = requests.get(f'{base}/sessions/113/captures', headers=h, verify=False)
caps = rc.json().get('captures', [])
print(f'Total captures: {len(caps)}')

# 模擬 avg_nz 計算 attention 和 meditation
attn_vals = [c.get('attention') for c in caps if c.get('attention') is not None]
medi_vals = [c.get('meditation') for c in caps if c.get('meditation') is not None]
delta_max = max(c.get('delta', 0) for c in caps)

print(f'delta_max={delta_max}, _is_raw={delta_max > 1000}')
print(f'attention: {len(attn_vals)} non-null vals, avg={round(sum(attn_vals)/len(attn_vals),2) if attn_vals else None}')
print(f'meditation: {len(medi_vals)} non-null vals, avg={round(sum(medi_vals)/len(medi_vals),2) if medi_vals else None}')

# 在 raw 模式下，過濾低品質秒
MIN_DELTA_QUALITY = 10000  # 假設值 - 實際 check
print(f'\n_is_raw mode: filter delta < {MIN_DELTA_QUALITY}')
good = [c for c in caps if c.get('delta', 0) >= MIN_DELTA_QUALITY]
print(f'good caps: {len(good)}')
attn_good = [c.get('attention') for c in good if c.get('attention') is not None]
medi_good = [c.get('meditation') for c in good if c.get('meditation') is not None]
print(f'attention (after filter): {len(attn_good)} vals, avg={round(sum(attn_good)/len(attn_good),2) if attn_good else None}')
print(f'meditation (after filter): {len(medi_good)} vals, avg={round(sum(medi_good)/len(medi_good),2) if medi_good else None}')

# 看第一筆 attention
print('\nFirst 5 captures attention/meditation/delta:')
for c in caps[:5]:
    print(f'  seq={c.get("seq_num")} attn={c.get("attention")} medi={c.get("meditation")} delta={c.get("delta")}')

# 看有無 attention=None 的 captures
null_attn = [c for c in caps if c.get('attention') is None]
print(f'\nCaptures with attention=None: {len(null_attn)}')
