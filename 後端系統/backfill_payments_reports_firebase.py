"""
backfill_payments_reports_firebase.py
========================================
將歷史付款記錄和報告 PDF 連結批次同步到 Firebase。

執行方式（Railway Console）：
    python backfill_payments_reports_firebase.py          # 全部跑
    python backfill_payments_reports_firebase.py --dry    # 只顯示，不真的寫入
    python backfill_payments_reports_firebase.py --payments-only
    python backfill_payments_reports_firebase.py --reports-only
"""
import sys, os, argparse, time
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.models import Payment, Session as SessionModel, Report
from app.services.firebase_sync import sync_payment_to_firebase, sync_report_pdf_to_firebase

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry",            action="store_true", help="Dry run，只列出不寫入")
    parser.add_argument("--payments-only",  action="store_true")
    parser.add_argument("--reports-only",   action="store_true")
    args = parser.parse_args()

    do_payments = not args.reports_only
    do_reports  = not args.payments_only

    db = SessionLocal()
    try:
        # ── 1. 付款記錄 ──────────────────────────────────────────────────────
        if do_payments:
            payments = db.query(Payment).filter(Payment.status == "paid").order_by(Payment.payment_id).all()
            print(f"\n=== 付款記錄：共 {len(payments)} 筆 status=paid ===")
            ok = fail = skip = 0
            for p in payments:
                data = {
                    "payment_id":    p.payment_id,
                    "order_id":      p.order_id,
                    "consultant_id": p.consultant_id,
                    "consultant_name": p.consultant_name,
                    "subject_name":  p.subject_name,
                    "subject_email": p.subject_email,
                    "report_type":   p.report_type,
                    "amount":        p.amount,
                    "status":        p.status,
                    "provider":      p.provider,
                    "payment_method":p.payment_method,
                    "paid_at":       p.paid_at,
                    "created_at":    p.created_at,
                }
                if args.dry:
                    print(f"  [DRY] payment_id={p.payment_id} subject={p.subject_name}")
                    skip += 1
                    continue
                result = sync_payment_to_firebase(data)
                if result:
                    ok += 1
                    print(f"  [OK]  payment_id={p.payment_id} {p.subject_name}")
                else:
                    fail += 1
                    print(f"  [FAIL] payment_id={p.payment_id} {p.subject_name}")
                time.sleep(0.1)  # 避免 Firebase rate limit
            print(f"付款同步結果：OK={ok} FAIL={fail} DRY={skip}")

        # ── 2. 報告 PDF 連結 ──────────────────────────────────────────────────
        if do_reports:
            reports = (db.query(Report, SessionModel)
                       .join(SessionModel, Report.session_id == SessionModel.session_id)
                       .filter(Report.status == "completed",
                               Report.pdf_url != None,
                               Report.pdf_url != "",
                               SessionModel.firebase_session_id != None)
                       .order_by(Report.report_id).all())
            print(f"\n=== 報告 PDF：共 {len(reports)} 筆有 pdfUrl 且有 firebase_session_id ===")
            ok = fail = skip = 0
            for rep, sess in reports:
                fb_sid = sess.firebase_session_id
                rt = sess.report_type or "adult"
                # 去除 GCS Signed URL 簽名參數，保留基礎 URL
                base_url = rep.pdf_url.split("?")[0] if rep.pdf_url else ""
                if not base_url:
                    skip += 1
                    continue
                if args.dry:
                    print(f"  [DRY] report_id={rep.report_id} fb_sid={fb_sid} rt={rt}")
                    skip += 1
                    continue
                result = sync_report_pdf_to_firebase(fb_sid, rt, base_url)
                if result:
                    ok += 1
                    print(f"  [OK]  report_id={rep.report_id} session={rep.session_id}")
                else:
                    fail += 1
                    print(f"  [FAIL] report_id={rep.report_id} session={rep.session_id} fb_sid={fb_sid}")
                time.sleep(0.1)
            print(f"報告同步結果：OK={ok} FAIL={fail} SKIP={skip}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
