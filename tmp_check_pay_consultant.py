"""
直接查 DB 確認 VIP 付款的 consultant_id 與 consultant_name 是否有值
"""
import sys, os
sys.path.insert(0, r'D:\Write program\AutomaticDetection\後端系統')
os.chdir(r'D:\Write program\AutomaticDetection\後端系統')

try:
    from app.core.database import SessionLocal
    from app.core import models as M
    from sqlalchemy import or_

    db = SessionLocal()
    rows = db.query(
        M.Payment.payment_id,
        M.Payment.subject_name,
        M.Payment.report_type,
        M.Payment.consultant_id,
        M.Payment.consultant_name,
        M.Payment.status,
    ).filter(
        M.Payment.report_type.in_(['life_vip', 'child_vip']),
        M.Payment.status == 'paid',
    ).order_by(M.Payment.payment_id.desc()).limit(30).all()

    print(f'VIP paid payments: {len(rows)}')
    print(f'{"subject_name":<20} {"consultant_id":>14} {"consultant_name":<20} {"type":<12}')
    print('-' * 75)
    cid_none = 0
    cname_none = 0
    for r in rows:
        cid = r.consultant_id
        cname = r.consultant_name or '(none)'
        if cid is None:
            cid_none += 1
        if not r.consultant_name:
            cname_none += 1
        print(f'{(r.subject_name or "?"):<20} {str(cid):>14} {cname:<20} {r.report_type:<12}')

    print()
    print(f'consultant_id=NULL: {cid_none}/{len(rows)}')
    print(f'consultant_name=NULL: {cname_none}/{len(rows)}')
    db.close()

except Exception as e:
    print(f'DB connection failed: {e}')
    print('Trying via API...')
    import requests, urllib3, json
    urllib3.disable_warnings()
    BASE = 'https://backend-production-2da61.up.railway.app'
    r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
    token = r.json().get('token')
    s = requests.Session()
    s.verify = False
    s.headers.update({'Authorization': 'Bearer ' + token})
    r2 = s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=20)
    pays = r2.json().get('payments', []) if r2.status_code == 200 else []
    vip = [p for p in pays if p.get('report_type') in ('life_vip','child_vip') and p.get('status')=='paid']
    print(f'VIP payments: {len(vip)}')
    # API 不回傳 consultant_id/consultant_name，但可確認至少有多少筆
    for p in vip[:5]:
        print(f'  {p.get("subject_name")} | type={p.get("report_type")}')
