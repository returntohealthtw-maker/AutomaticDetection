"""診斷 60 筆 FAIL 付款：有 session 但未同步 Firebase / 還是完全沒有 session"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.models import Payment, Session as SessionModel

db = SessionLocal()
try:
    payments = db.query(Payment).filter(Payment.status == "paid").order_by(Payment.payment_id).all()

    # 找出「有 paid 付款、但沒有 firebase_session_id 的 session」
    # 同時找出「完全沒有 session」的
    name_to_sessions: dict[str, list] = {}
    for s in db.query(SessionModel).all():
        if s.subject_name:
            name_to_sessions.setdefault(s.subject_name, []).append(s)

    no_session = []        # 完全沒有 session
    has_session_no_fb = [] # 有 session 但都沒有 firebase_session_id
    ok_with_fb = []        # 已有 firebase_session_id（本來就 OK 的）

    for p in payments:
        sessions = name_to_sessions.get(p.subject_name, [])
        has_fb = any(s.firebase_session_id for s in sessions)
        if has_fb:
            ok_with_fb.append(p)
        elif sessions:
            has_session_no_fb.append((p, sessions))
        else:
            no_session.append(p)

    print(f"已有 firebase_session_id（OK）: {len(ok_with_fb)} 筆")
    print(f"有 session 但未同步 Firebase: {len(has_session_no_fb)} 筆 ← 可修復")
    print(f"完全沒有 session: {len(no_session)} 筆 ← 需要 Firebase CF 新增端點")

    if has_session_no_fb:
        print("\n可修復的付款（需先同步 session 到 Firebase）：")
        for p, sessions in has_session_no_fb[:10]:
            print(f"  payment_id={p.payment_id} {p.subject_name}  sessions={[s.session_id for s in sessions]}")
        if len(has_session_no_fb) > 10:
            print(f"  ... 共 {len(has_session_no_fb)} 筆")

    if no_session:
        print("\n完全沒有 session 的付款（這些人還沒做過腦波檢測）：")
        for p in no_session[:10]:
            print(f"  payment_id={p.payment_id} {p.subject_name}")
        if len(no_session) > 10:
            print(f"  ... 共 {len(no_session)} 筆")

finally:
    db.close()
