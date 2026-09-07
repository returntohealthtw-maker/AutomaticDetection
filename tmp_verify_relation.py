"""
顧問角度驗證關係報告（親子/夫妻/情侶）流程
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'

def login(phone, password):
    r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone': phone, 'password': password}, verify=False, timeout=15)
    if r.status_code != 200:
        print(f'[FAIL] Login failed: {r.status_code} {r.text[:200]}')
        return None
    return r.json().get('token')

def make_session(token):
    s = requests.Session()
    s.verify = False
    s.headers.update({'Authorization': f'Bearer {token}'})
    return s

print('=' * 60)
print('【步驟 1】Admin 登入')
token = login('0900000000', 'admin123')
if not token:
    sys.exit(1)
print(f'  [OK] 登入成功')
s = make_session(token)

print()
print('=' * 60)
print('【步驟 2】載入 VIP 名單（模擬前端 _loadVipCustomers）')

r_pay = s.get(f'{BASE}/api/v1/payments/my?limit=200')
r_sess = s.get(f'{BASE}/api/v1/eeg/sessions?limit=200')

print(f'  Payments API: {r_pay.status_code}')
print(f'  Sessions API: {r_sess.status_code}')

payments = []
sessions = []
if r_pay.status_code == 200:
    data = r_pay.json()
    payments = data.get('payments', data) if isinstance(data, dict) else data
if r_sess.status_code == 200:
    data = r_sess.json()
    sessions = data.get('sessions', data) if isinstance(data, dict) else data

VIP_TYPES = {'life_vip', 'child_vip'}
vip_paid = [p for p in payments if p.get('report_type') in VIP_TYPES and p.get('status') == 'paid']

session_by_name = {}
for ss in sessions:
    nm = ss.get('subject_name', '')
    if nm and nm not in session_by_name:
        session_by_name[nm] = ss

print(f'  Total payments: {len(payments)}, VIP paid: {len(vip_paid)}')
print(f'  Total sessions: {len(sessions)}')

by_name = {}
for p in vip_paid:
    nm = p.get('subject_name', '')
    if not nm:
        continue
    if nm not in by_name or (p.get('paid_at', 0) or 0) > (by_name[nm].get('paid_at', 0) or 0):
        by_name[nm] = p

vip_customers = []
for i, (nm, p) in enumerate(by_name.items()):
    sess = session_by_name.get(nm, {})
    vip_customers.append({
        'id': f'p{i}',
        'name': nm,
        'age': sess.get('subject_age'),
        'session_id': sess.get('session_id'),
        'report_type': p.get('report_type'),
        'email': p.get('subject_email', ''),
    })

print(f'  VIP customers found: {len(vip_customers)}')
for vc in vip_customers:
    sid = vc.get('session_id')
    print(f'    {vc["name"]} | age={vc["age"]} | session_id={sid} | type={vc["report_type"]}')

if len(vip_customers) < 2:
    print()
    print('[WARNING] VIP 名單人數不足（需至少 2 人才能生成關係報告）')
    print('  這是正常的，若顧問尚未有 VIP 付款客戶，關係報告按鈕會顯示空名單')

print()
print('=' * 60)
print('【步驟 3】驗證夫妻報告外部系統連線')
MARITAL_URL = 'https://web-production-2c7d43.up.railway.app'
try:
    r_m = requests.get(f'{MARITAL_URL}/health', timeout=10, verify=False)
    print(f'  夫妻系統 /health: {r_m.status_code}')
    if r_m.status_code == 200:
        print(f'    [OK] 夫妻外部系統正常')
    else:
        print(f'    [WARN] 回應: {r_m.text[:200]}')
except Exception as e:
    print(f'  [FAIL] 夫妻外部系統連線失敗: {e}')

print()
print('=' * 60)
print('【步驟 4】驗證親子報告本機服務')
try:
    r_pc = s.get(f'{BASE}/api/v1/parent-child/health', timeout=10)
    print(f'  親子 /health: {r_pc.status_code}')
    if r_pc.status_code == 200:
        print(f'    [OK] 親子本機服務正常: {r_pc.text[:200]}')
    else:
        print(f'    [WARN] {r_pc.text[:200]}')
except Exception as e:
    print(f'  [INFO] 親子 health 路由不存在或連線失敗: {e}')

print()
print('=' * 60)
print('【步驟 5】驗證 report-gen/start API（使用 2 個 VIP session 生成夫妻報告）')
if len(vip_customers) >= 2:
    p0 = vip_customers[0]
    p1 = vip_customers[1]
    
    if not p0.get('session_id') or not p1.get('session_id'):
        print(f'  [WARN] 有 VIP 客戶但缺少 session_id，無法測試關係報告生成')
        print(f'    {p0["name"]}: session_id={p0.get("session_id")}')
        print(f'    {p1["name"]}: session_id={p1.get("session_id")}')
    else:
        payload = {
            'subject_name': p0['name'],
            'subject_email': p0.get('email') or None,
            'subject_age': p0.get('age'),
            'subject_gender': '',
            'report_type': 'marital',
            'variant': 'vip',
            'session_id': p0['session_id'],
            'brainwave_data': None,
            'extra': {
                'husband_name': p0['name'],
                'husband_session_id': p0['session_id'],
                'wife_name': p1['name'],
                'wife_session_id': p1['session_id'],
            },
        }
        print(f'  Payload: {json.dumps(payload, ensure_ascii=False, default=str)[:400]}')
        # 注意：這裡只驗證 API 是否接受請求，不會真的生成報告
        # r_gen = s.post(f'{BASE}/api/v1/report-gen/start', json=payload, timeout=30)
        # print(f'  report-gen/start: {r_gen.status_code}')
        print()
        print('  [NOTE] 未實際觸發報告生成（需使用者授權）')
else:
    print('  [SKIP] VIP 客戶不足 2 人，跳過此測試')

print()
print('=' * 60)
print('【步驟 6】確認親子報告本機 parent_child_data 目錄是否存在')
r_diag = s.get(f'{BASE}/api/v1/report-gen/health', timeout=15)
print(f'  report-gen/health: {r_diag.status_code}')
if r_diag.status_code == 200:
    diag = r_diag.json()
    print(f'  external_reports: {json.dumps(diag.get("external_reports", {}), ensure_ascii=False, indent=4)}')
    print(f'  mock_mode: {diag.get("mock_mode")}')
    print(f'  gemini_key_set: {diag.get("gemini_key_set")}')

print()
print('=' * 60)
print('驗證完成')
