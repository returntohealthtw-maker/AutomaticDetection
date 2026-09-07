import requests, json, time, sys

BASE = "https://backend-production-2da61.up.railway.app/api/v1"

# 1. Login as admin
r = requests.post(f"{BASE}/auth/login", json={"phone": "0900000000", "password": "admin123"}, timeout=30)
r.raise_for_status()
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("[1] login ok")

# 2. Synthetic 15-year-old teen brainwave data (valid, non-zero, sample_count>=30)
brainwave_data = {
    "sample_count": 180,
    "attention_percentage": 62,
    "meditation_percentage": 48,
    "bands_avg": {
        "delta": 40, "theta": 35, "alpha": 55, "beta": 60, "gamma": 30,
        "low_alpha": 50, "high_alpha": 58, "low_beta": 55, "high_beta": 62,
        "low_gamma": 28, "high_gamma": 33,
    },
    "bands_7": {
        "delta": 40, "theta": 35,
        "alpha_low": 50, "alpha_high": 58,
        "beta_low": 55, "beta_high": 62,
        "gamma_low": 28, "gamma_high": 33,
    },
}

payload = {
    "subject_name": "_test_teen_e2e",
    "subject_age": 15,
    "subject_gender": "female",
    "report_type": "teen",
    "variant": "trial",
    "brainwave_data": brainwave_data,
    "subject_email": None,
    "chapters_to_generate": None,
}

r = requests.post(f"{BASE}/report-gen/start", json=payload, headers=headers, timeout=60)
print("[2] start status:", r.status_code)
print(r.text[:2000])
data = r.json()
job_id = data.get("job_id")
print("job_id =", job_id, "mode =", data.get("mode"))

if not job_id:
    sys.exit(0)

# 3. Poll active-jobs until done or timeout (max ~12 min)
deadline = time.time() + 12 * 60
last_status = None
while time.time() < deadline:
    r = requests.get(f"{BASE}/report-gen/active-jobs", headers=headers, timeout=30)
    jobs = r.json().get("jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job:
        print("[poll] job not in active list anymore (likely finished/removed)")
        break
    if job.get("status") != last_status:
        print(f"[poll] status={job.get('status')} elapsed={job.get('elapsed_sec')}s preview={job.get('page_text_preview','')[:100]!r}")
        last_status = job.get("status")
    if job.get("status") in ("completed", "failed"):
        print("[poll] FINAL:", json.dumps(job, ensure_ascii=False, indent=2)[:2000])
        break
    time.sleep(15)
else:
    print("[poll] TIMEOUT waiting for job")
