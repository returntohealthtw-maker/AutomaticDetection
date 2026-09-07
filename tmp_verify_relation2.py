"""
深度驗證關係報告流程 - 測試 API 連線與資料流
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'

r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': f'Bearer {token}'})

print('=== 驗證1: 親子外部系統連線 ===')
PC_URL = 'https://web-production-f1aec.up.railway.app'
try:
    r_pc = requests.get(f'{PC_URL}/', timeout=10, verify=False)
    print(f'親子系統 GET /: {r_pc.status_code}')
    if r_pc.status_code in (200, 405):
        print('  [OK] 親子系統有回應')
    else:
        print(f'  [WARN] {r_pc.text[:200]}')
except Exception as e:
    print(f'  [FAIL] 連線失敗: {e}')

try:
    r_pc2 = requests.get(f'{PC_URL}/health', timeout=10, verify=False)
    print(f'親子系統 /health: {r_pc2.status_code} {r_pc2.text[:200]}')
except Exception as e:
    print(f'  /health 失敗: {e}')

print()
print('=== 驗證2: 夫妻外部系統連線 ===')
MARITAL_URL = 'https://web-production-2c7d43.up.railway.app'
try:
    r_m = requests.get(f'{MARITAL_URL}/', timeout=10, verify=False)
    print(f'夫妻系統 GET /: {r_m.status_code}')
    if r_m.status_code in (200, 405):
        print('  [OK] 夫妻系統有回應')
    else:
        print(f'  [WARN] {r_m.text[:200]}')
except Exception as e:
    print(f'  [FAIL] 連線失敗: {e}')

try:
    r_m2 = requests.get(f'{MARITAL_URL}/health', timeout=10, verify=False)
    print(f'夫妻系統 /health: {r_m2.status_code} {r_m2.text[:200]}')
except Exception as e:
    print(f'  /health 失敗: {e}')

print()
print('=== 驗證3: Session #112 腦波資料是否足夠生成報告 ===')
# 以第一個 VIP 客戶（session 112）為例
for sid in [112, 111]:
    r_stats = s.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats')
    if r_stats.status_code == 200:
        stats = r_stats.json()
        sample_count = stats.get('sample_count', 0)
        bands = stats.get('bands_avg') or {}
        q = stats.get('qeeg_abilities') or {}
        print(f'Session #{sid}: sample_count={sample_count}, has_bands={bool(bands)}, has_qeeg={bool(q)}')
        print(f'  bands_avg.theta={bands.get("theta")}, focus={q.get("focus")}, relaxation={q.get("relaxation")}')
    else:
        print(f'Session #{sid} stats: {r_stats.status_code} {r_stats.text[:100]}')

print()
print('=== 驗證4: 測試 report-gen/start 夫妻報告（不實際生成，只測 API） ===')
# 用 session 112（徐嬌嬌） + 111（姜燕明） 測試
payload = {
    'subject_name': '徐嬌嬌',
    'subject_email': None,
    'subject_age': 39,
    'subject_gender': '',
    'report_type': 'marital',
    'variant': 'vip',
    'session_id': 112,
    'brainwave_data': None,
    'extra': {
        'husband_name': '徐嬌嬌',
        'husband_session_id': 112,
        'wife_name': '姜燕明',
        'wife_session_id': 111,
    },
}
print(f'  Payload report_type=marital, sessions={112},{111}')
# 注意：這裡只進行「試呼叫」，確認 API 回應
r_start = s.post(f'{BASE}/api/v1/report-gen/start', json=payload, timeout=120)
print(f'  report-gen/start status: {r_start.status_code}')
if r_start.status_code == 200:
    resp = r_start.json()
    print(f'  [OK] mode={resp.get("mode")}, external_mode={resp.get("external_mode")}')
    if resp.get('ok'):
        print(f'  [SUCCESS] 關係報告啟動成功')
        print(f'  result_url={resp.get("result_url")}')
        print(f'  job_id={resp.get("job_id")}')
    else:
        print(f'  [FAIL] ok=False, error={resp.get("error")}')
elif r_start.status_code == 400:
    detail = r_start.json().get('detail', {})
    print(f'  [400] {detail}')
else:
    print(f'  [ERROR] {r_start.text[:400]}')

print()
print('=== 驗證5: 親子報告（3 人）測試 ===')
# 找3個 VIP session
r_sessions = s.get(f'{BASE}/api/v1/eeg/sessions?limit=200')
all_sessions = r_sessions.json().get('sessions', []) if r_sessions.status_code == 200 else []
r_pay = s.get(f'{BASE}/api/v1/payments/my?limit=200')
all_payments = r_pay.json().get('payments', []) if r_pay.status_code == 200 else []
VIP_TYPES = {'life_vip', 'child_vip'}
vip_paid_names = {p.get('subject_name') for p in all_payments if p.get('report_type') in VIP_TYPES and p.get('status') == 'paid'}
vip_sessions = [ss for ss in all_sessions if ss.get('subject_name') in vip_paid_names and ss.get('session_id')]
print(f'  VIP sessions available: {len(vip_sessions)}')
if len(vip_sessions) >= 3:
    members = [
        {'role': 'dad', 'role_zh': '爸爸', 'name': vip_sessions[0].get('subject_name'), 'present': True, 'session_id': vip_sessions[0].get('session_id'), 'data': None},
        {'role': 'mom', 'role_zh': '媽媽', 'name': vip_sessions[1].get('subject_name'), 'present': True, 'session_id': vip_sessions[1].get('session_id'), 'data': None},
        {'role': 'child1', 'role_zh': '孩子1', 'name': vip_sessions[2].get('subject_name'), 'present': True, 'session_id': vip_sessions[2].get('session_id'), 'data': None},
    ]
    pc_payload = {
        'subject_name': members[0]['name'],
        'subject_email': None,
        'subject_age': None,
        'subject_gender': '',
        'report_type': 'parent_child',
        'variant': 'vip',
        'session_id': members[0]['session_id'],
        'brainwave_data': None,
        'extra': {
            'family_name': members[0]['name'][0] + '家',
            'members': members,
        },
    }
    print(f'  Testing parent_child with: {[m["name"] for m in members]}')
    r_pc_start = s.post(f'{BASE}/api/v1/report-gen/start', json=pc_payload, timeout=120)
    print(f'  report-gen/start status: {r_pc_start.status_code}')
    if r_pc_start.status_code == 200:
        resp = r_pc_start.json()
        print(f'  [OK] mode={resp.get("mode")}, external_mode={resp.get("external_mode")}')
        if resp.get('ok'):
            print(f'  [SUCCESS] 親子報告啟動成功')
            print(f'  result_url={resp.get("result_url")}')
        else:
            print(f'  [FAIL] ok=False, error={resp.get("error")}')
    elif r_pc_start.status_code == 400:
        detail = r_pc_start.json().get('detail', {})
        print(f'  [400] {detail}')
    else:
        print(f'  [ERROR] {r_pc_start.text[:400]}')
else:
    print(f'  [SKIP] VIP sessions < 3，跳過親子報告測試')

print()
print('驗證完成')
