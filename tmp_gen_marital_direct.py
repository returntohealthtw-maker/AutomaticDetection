"""
直接生成夫妻報告：
1. 從後端 API 取洪任佑(112) 和 王筱琪(49) 的腦波數據
2. 呼叫夫妻報告服務
3. 上傳 GCS
4. 更新 report #130
"""
import sys, requests, urllib3, json, time, uuid
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
MARITAL = 'https://web-production-2c7d43.up.railway.app'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# ── 1. 取後台顯示的洪任佑腦波 (session 112) ──
print("=== 取洪任佑腦波 ===")
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=200&offset=0', headers=h, verify=False)
subjects = ov.json()
if isinstance(subjects, dict):
    subjects = subjects.get('subjects') or subjects.get('data') or []

hong_bw = None
wang_bw = None

for s in subjects:
    name = s.get('name') or s.get('subject_name', '')
    if '洪任佑' in name:
        hong_bw = s.get('latest_brainwave') or {}
        print(f"洪任佑 bw source={hong_bw.get('_source')}")
        ba = hong_bw.get('bands_avg') or {}
        print(f"  Delta={ba.get('delta')} Theta={ba.get('theta')} High_a={ba.get('high_alpha')} Low_a={ba.get('low_alpha')}")
    if '王筱琪' in name:
        wang_bw = s.get('latest_brainwave') or {}
        print(f"王筱琪 bw source={wang_bw.get('_source')}")
        ba = wang_bw.get('bands_avg') or {}
        print(f"  Delta={ba.get('delta')} Theta={ba.get('theta')} High_a={ba.get('high_alpha')} Low_a={ba.get('low_alpha')}")

if not hong_bw or not wang_bw:
    print("ERROR: 找不到腦波資料")
    sys.exit(1)

def bw_to_7indices(bw):
    """轉換成夫妻報告服務需要的 7 指標格式"""
    ba = bw.get('bands_avg') or {}
    bdna = bw.get('braindna') or {}
    def g(key, default=50):
        v = ba.get(key)
        if v is None:
            v = bdna.get(key)
        return float(v) if v is not None else float(default)
    return {
        "delta":      g("delta"),
        "theta":      g("theta"),
        "low_alpha":  g("low_alpha"),
        "high_alpha": g("high_alpha"),
        "low_beta":   g("low_beta"),
        "high_beta":  g("high_beta"),
        "low_gamma":  g("low_gamma"),
    }

hong_7 = bw_to_7indices(hong_bw)
wang_7 = bw_to_7indices(wang_bw)
print("\n洪任佑 7 指標:", json.dumps(hong_7, ensure_ascii=False))
print("王筱琪 7 指標:", json.dumps(wang_7, ensure_ascii=False))

# ── 2. 取受測者基本資料 ──
def get_subject_info(session_id):
    sr = requests.get(BASE+f'/eeg/sessions/{session_id}/stats', headers=h, verify=False)
    d = sr.json()
    return {
        'name': d.get('subject_name') or '',
        'age': d.get('subject_age') or 0,
    }

hong_info = get_subject_info(112)
wang_info = get_subject_info(49)
print(f"\n洪任佑: name={hong_info['name']}, age={hong_info['age']}")
print(f"王筱琪: name={wang_info['name']}, age={wang_info['age']}")

# ── 3. 呼叫夫妻報告 API ──
print("\n=== 呼叫夫妻報告 API ===")
payload = {
    "report_id": f"marital-{uuid.uuid4().hex[:8]}",
    "test_date": time.strftime("%Y-%m-%d"),
    "marriage_years": 0,
    "has_children": False,
    "children_info": "",
    "notes": "",
    "husband": {
        "name": hong_info['name'] or "洪任佑",
        "age": int(hong_info['age'] or 0),
        "brainwave": hong_7,
    },
    "wife": {
        "name": wang_info['name'] or "王筱琪",
        "age": int(wang_info['age'] or 0),
        "detected_at": "",
        "brainwave": wang_7,
    },
}

print("Payload husband:", payload['husband']['name'], "wife:", payload['wife']['name'])
print("Calling", MARITAL + "/api/generate")

start = time.time()
mr = requests.post(MARITAL + '/api/generate', json=payload, timeout=300, verify=False)
elapsed = time.time() - start
print(f"Response: {mr.status_code}, elapsed={elapsed:.1f}s, content-type={mr.headers.get('content-type')}, size={len(mr.content)}")

if mr.status_code >= 400:
    print("ERROR:", mr.text[:500])
    sys.exit(1)

if mr.content[:4] != b'%PDF' and 'pdf' not in mr.headers.get('content-type', '').lower():
    print("Non-PDF response:", mr.text[:300])
    sys.exit(1)

print(f"Got PDF: {len(mr.content)} bytes")

# ── 4. 上傳到 GCS ──
print("\n=== 上傳 GCS ===")
job_id = f"marital-{uuid.uuid4().hex[:12]}"
gcs_ur = requests.post(BASE+'/reports/130/upload-pdf',
    headers=h,
    files={'file': (f'{job_id}.pdf', mr.content, 'application/pdf')},
    verify=False)
print("GCS upload:", gcs_ur.status_code, gcs_ur.text[:300])
if gcs_ur.ok:
    pdf_url = gcs_ur.json().get('pdf_url') or gcs_ur.json().get('url') or ''
    print("PDF URL:", pdf_url[:80])
    # Update report #130 status to completed
    summary = {'subject_name':'洪任佑','source':'marital_rest',
               'husband_session_id':112,'husband_name':'洪任佑',
               'wife_session_id':49,'wife_name':'王筱琪'}
    fin = requests.post(BASE+'/reports/130/update-summary',
        json={'status':'completed', 'pdf_url': pdf_url,
              'client_summary': json.dumps(summary, ensure_ascii=False)},
        headers=h, verify=False)
    print("Finalize:", fin.status_code, fin.text[:200])
