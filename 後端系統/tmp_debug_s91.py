import requests, json, warnings
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(f'{BASE}/auth/login',
    json={'phone':'0900000000','password':'admin123'}, verify=False)
tok = r.json().get('token','')
headers = {'Authorization': f'Bearer {tok}'}

SID = 91

# 取完整 captures，看 seq_num 分布
r4 = requests.get(f'{BASE}/sessions/{SID}/captures', headers=headers, verify=False)
caps_data = r4.json()
cap_list = caps_data if isinstance(caps_data, list) else caps_data.get('captures', [])

print(f'Session {SID}: 共 {len(cap_list)} 筆 captures')

# 看 seq_num 的分布
seqs = sorted([c.get('seq_num', -1) for c in cap_list])
print(f'seq_num 範圍: {min(seqs)} ~ {max(seqs)}')
print(f'seq_num=0 的筆數: {sum(1 for s in seqs if s == 0)}')

# 看 seq_num=0 是否有特殊值（stats record）
s0 = [c for c in cap_list if c.get('seq_num') == 0]
if s0:
    print(f'\nseq_num=0 的資料:')
    for c in s0:
        print(' ', c)

# 看前 5 筆
print(f'\n前 5 筆 seq_num 排序後:')
sorted_caps = sorted(cap_list, key=lambda c: c.get('seq_num', 0))
for c in sorted_caps[:5]:
    fields = ['seq_num','is_baseline','good_signal','delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
    row = {k: c.get(k) for k in fields}
    print(' ', row)

# 統計 low_alpha vs high_alpha 的差異
diffs = [abs((c.get('low_alpha') or 0) - (c.get('high_alpha') or 0)) for c in cap_list]
print(f'\nlow_alpha vs high_alpha 差值: avg={sum(diffs)/len(diffs):.2f}, max={max(diffs)}, min={min(diffs)}')

diffs_b = [abs((c.get('low_beta') or 0) - (c.get('high_beta') or 0)) for c in cap_list]
print(f'low_beta vs high_beta 差值:   avg={sum(diffs_b)/len(diffs_b):.2f}, max={max(diffs_b)}, min={min(diffs_b)}')

diffs_g = [abs((c.get('low_gamma') or 0) - (c.get('high_gamma') or 0)) for c in cap_list]
print(f'low_gamma vs high_gamma 差值: avg={sum(diffs_g)/len(diffs_g):.2f}, max={max(diffs_g)}, min={min(diffs_g)}')

# 看前幾個 delta 值（raw ThinkGear 應該是 10000+）
deltas = [c.get('delta') for c in sorted_caps[:10]]
print(f'\n前10筆 delta 值: {deltas}')
print(f'（raw ThinkGear delta 應該 > 10000，若 < 200 表示是 bandTo100 正規化值）')
