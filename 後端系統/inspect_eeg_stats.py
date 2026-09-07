import sys, io, requests, json, urllib3, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.algorithms import (
    build_mbti_payload, BandAverages,
    _calc_mind_color, _MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW,
)

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

all_sess = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15).json().get("sessions", [])
seen = {}; recent = []
for sess in sorted(all_sess, key=lambda x: x.get("created_at",""), reverse=True):
    name = sess.get("subject_name") or "Unknown"
    sid  = sess.get("session_id") or sess.get("id")
    if name not in seen and sid:
        seen[name] = True
        recent.append({"name": name, "sid": sid})
    if len(recent) >= 3:
        break

MC_NAMES = {_MC_ORANGE:"橙", _MC_GREEN:"綠", _MC_BLUE:"藍", _MC_YELLOW:"黃"}

for item in recent:
    name = item["name"]
    sid  = item["sid"]
    print(f"\n{'='*65}")
    print(f"  受測者：{name}  │  Session ID: {sid}")
    print('='*65)

    rs = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=15).json()
    eeg = rs.get("eeg_stats") or {}
    bands_avg = eeg.get("bands_avg") or {}
    bands_7   = eeg.get("bands_7") or {}

    # Print raw structure
    print(f"  bands_avg: {json.dumps(bands_avg, ensure_ascii=False)[:300]}")
    print(f"  bands_7 keys: {list(bands_7.keys()) if isinstance(bands_7, dict) else type(bands_7)}")

    # The bands_avg likely has the band names as keys with 0-100 values
    def _g(*keys, src=bands_avg, default=0.0):
        for k in keys:
            if k in src:
                v = src[k]
                return float(v) if v is not None else default
        return default

    # Try both naming conventions
    la = _g("low_alpha", "lowAlpha")
    th = _g("theta")
    ha = _g("high_alpha", "highAlpha")
    hb = _g("high_beta", "highBeta")
    lb = _g("low_beta", "lowBeta")
    lg = _g("low_gamma", "lowGamma")
    hg = _g("high_gamma", "highGamma")
    at = _g("attention")
    md = _g("meditation")

    print(f"  la={la:.1f} th={th:.1f} ha={ha:.1f} hb={hb:.1f} lb={lb:.1f} lg={lg:.1f} hg={hg:.1f}")

    if la == 0 and th == 0:
        # Try bands_7 structure
        print(f"  bands_7: {json.dumps(bands_7, ensure_ascii=False)[:400]}")
