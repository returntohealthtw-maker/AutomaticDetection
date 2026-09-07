import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core import models as M

db = SessionLocal()
try:
    p = db.query(M.Payment).filter(M.Payment.payment_id == 188).first()
    if p:
        print(f"Payment 188:")
        print(f"  consultant_id = {p.consultant_id}")
        print(f"  subject_name  = {p.subject_name}")
        print(f"  status        = {p.status}")
        print(f"  report_type   = {p.report_type}")
        print(f"  subject_id    = {getattr(p, 'subject_id', 'N/A')}")
    else:
        print("Payment 188 not found")

    pays = db.query(M.Payment).filter(M.Payment.subject_name.like('%莊子渝%')).all()
    print(f"\n莊子渝全部付款: {len(pays)} 筆")
    for p2 in pays:
        print(f"  id={p2.payment_id} consultant_id={p2.consultant_id} status={p2.status} report={p2.report_type}")

    pays15 = db.query(M.Payment).filter(M.Payment.consultant_id == 15, M.Payment.status == 'paid').all()
    print(f"\nConsultant 15 的 paid 付款: {len(pays15)} 筆")
    for p3 in pays15:
        print(f"  id={p3.payment_id} subject={p3.subject_name} report={p3.report_type}")
finally:
    db.close()
