"""透過 Railway API 診斷 60 筆 FAIL 付款"""
import requests, json

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
h = {'Authorization': f'Bearer {token}'}

# 取所有 paid payments（admin 看全部）
r = requests.get(f'{base}/payments/admin/paid-not-detected?days=3650', headers=h)
orders = r.json().get('orders', [])

# 取所有 sessions（從 subjects overview 拿）
subj_r = requests.get(f'{base}/reports/all-subjects-overview?limit=1000', headers=h)
subjects = subj_r.json().get('subjects', [])

# 建立 subject_name → latest firebase_session_id 對應
name_to_fb = {}
for s in subjects:
    bw = s.get('latest_brainwave') or {}
    # 找 session stats 的 firebase_session_id（all-subjects-overview 不直接回傳）
    # 用 latest_session_id 查
    pass

# 改用 sessions list 建立對應
sess_r = requests.get(f'{base}/eeg/sessions?limit=500', headers=h)
sessions = sess_r.json() if isinstance(sess_r.json(), list) else sess_r.json().get('sessions', [])

name_to_fb_sid = {}   # subject_name → firebase_session_id
name_to_sess_ids = {} # subject_name → [session_id, ...]

for s in sessions:
    name = s.get('subject_name', '')
    sid = s.get('session_id')
    fb_sid = s.get('firebase_session_id', '')
    if name:
        name_to_sess_ids.setdefault(name, []).append(sid)
        if fb_sid and name not in name_to_fb_sid:
            name_to_fb_sid[name] = fb_sid

# 所有 paid payments（用 admin 查全部 payments 表）
all_paid_r = requests.get(f'{base}/monitor/sessions?limit=1', headers=h)  # 先確認 monitor 是否可用
print(f"monitor status: {all_paid_r.status_code}")

# 直接分析 paid-not-detected 中 FAIL 的情況（fb_sid=無 的那些）
no_session_names = []
has_session_no_fb_names = []

# 從 backfill 輸出中我們知道以下名字失敗，這裡分析原因
# 先直接查所有 paid payments 並分類
payments_r = requests.get(f'{base}/payments/admin/paid-not-detected?days=3650', headers=h)
all_orders = payments_r.json().get('orders', [])

print(f"\n付款重測名單共 {len(all_orders)} 筆")
print("分析是否有 firebase_session_id...")

no_sess = []
sess_no_fb = []
has_fb = []

for o in all_orders:
    name = o.get('subject_name', '')
    fb_sid = name_to_fb_sid.get(name, '')
    sess_ids = name_to_sess_ids.get(name, [])
    if fb_sid:
        has_fb.append(name)
    elif sess_ids:
        sess_no_fb.append((name, sess_ids))
    else:
        no_sess.append(name)

print(f"\n有 firebase_session_id: {len(has_fb)} 筆")
print(f"有 session 但未同步 Firebase: {len(sess_no_fb)} 筆 ← 可修復（重新同步 session）")
print(f"完全沒有 session: {len(no_sess)} 筆 ← 需要 Firebase CF 新增端點")

if sess_no_fb:
    print(f"\n可修復的（前10筆）：")
    for name, sids in sess_no_fb[:10]:
        print(f"  {name} sessions={sids}")

if no_sess:
    print(f"\n完全無 session（前10筆）：")
    for name in no_sess[:10]:
        print(f"  {name}")
