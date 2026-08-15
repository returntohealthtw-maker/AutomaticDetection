import sys, io, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

SESSIONS = [
    {"sid": 52, "name": "鄭小怡"},
    {"sid": 49, "name": "王筱琪"},
    {"sid": 48, "name": "紀羽珊"},
]

for item in SESSIONS:
    sid  = item["sid"]
    name = item["name"]
    rs = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=15).json()
    eeg = rs.get("eeg_stats") or {}
    bands = eeg.get("bands_avg") or {}
    
    print(f"\n===== [{sid}] {name} =====")
    print(f"  sample_count = {eeg.get('sample_count')}")
    print(f"  bands_avg:")
    for k, v in sorted(bands.items()):
        print(f"    {k:20s} = {v}")
