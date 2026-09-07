import requests, json, time, sys

BASE = "https://backend-production-2da61.up.railway.app/api/v1"

# 0. Ensure demo direct-consultant account exists
r = requests.post(f"{BASE}/auth/bootstrap-direct-demo", timeout=30)
print("[0] bootstrap-direct-demo:", r.status_code, r.text[:150])

# 1. Login as demo consultant (non-admin)
r = requests.post(f"{BASE}/auth/login", json={"phone": "0900000002", "password": "direct123"}, timeout=30)
r.raise_for_status()
me = r.json()
token = me["token"]
headers = {"Authorization": f"Bearer {token}"}
print("[1] login as consultant ok, role=", me.get("role") or me.get("consultant", {}).get("role"))
print(json.dumps(me, ensure_ascii=False)[:500])

# 2. Create test subject, ~15 years old
birth = "2011-03-15"  # as of 2026-08-01 -> 15 years old
subj_payload = {
    "name": "_test顧問驗證_青少年",
    "birth_date": birth,
    "gender": "男",
    "occupation": "學生",
    "email": "test_consultant_verify@example.com",
    "phone": "0911222333",
}
r = requests.post(f"{BASE}/subjects", json=subj_payload, headers=headers, timeout=30)
print("[2] create subject:", r.status_code, r.text[:300])
subj = r.json()
subject_id = subj["subject_id"]
print("subject_id =", subject_id)

# 3. Save EEG stats (simulate WebApp collection) -> creates Session
eeg_payload = {
    "subject_name": "_test顧問驗證_青少年",
    "subject_birthday": birth,
    "subject_gender": "男",
    "subject_age": 15,
    "subject_id": subject_id,
    "report_type": "teen_trial",
    "sample_count": 180,
    "attention_percentage": 58,
    "meditation_percentage": 52,
    "bands_avg": {
        "delta": 42, "theta": 33, "alpha": 55, "beta": 58, "gamma": 31,
        "low_alpha": 48, "high_alpha": 57, "low_beta": 53, "high_beta": 60,
        "low_gamma": 27, "high_gamma": 34,
    },
}
r = requests.post(f"{BASE}/eeg/save-stats", json=eeg_payload, headers=headers, timeout=60)
print("[3] save-stats:", r.status_code, r.text[:500])
sess = r.json()
session_id = sess["session_id"]
print("session_id =", session_id)

# 4. Trigger teen trial report generation as the consultant (not admin)
gen_payload = {
    "subject_name": "_test顧問驗證_青少年",
    "subject_age": 15,
    "subject_gender": "男",
    "subject_id": subject_id,
    "report_type": "teen",
    "variant": "trial",
    "session_id": session_id,
}
r = requests.post(f"{BASE}/report-gen/start", json=gen_payload, headers=headers, timeout=60)
print("[4] start:", r.status_code, r.text[:1000])
data = r.json()
job_id = data.get("job_id")
print("job_id =", job_id)

if not job_id:
    sys.exit(0)

with open("_tmp_consultant_test_ids.json", "w", encoding="utf-8") as f:
    json.dump({"subject_id": subject_id, "session_id": session_id, "job_id": job_id}, f)

# 5. Poll
deadline = time.time() + 14 * 60
last = None
while time.time() < deadline:
    r = requests.get(f"{BASE}/report-gen/active-jobs", headers=headers, timeout=30)
    jobs = r.json().get("jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job:
        print("[poll] job left active list")
        break
    if job.get("status") != last:
        print(f"[poll] status={job.get('status')} elapsed={job.get('elapsed_sec')}s")
        last = job.get("status")
    if job.get("status") in ("completed", "failed"):
        print("[poll] FINAL", json.dumps(job, ensure_ascii=False)[:500])
        break
    time.sleep(15)
else:
    print("[poll] TIMEOUT")
