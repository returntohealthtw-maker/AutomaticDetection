"""
深入追蹤：比較三人的腦波差異與演算法決策路徑
"""
import sys, io, requests, urllib3, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

# ── 複製演算法邏輯（本地執行）────────────────────────────
_MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW = 0, 1, 2, 3
_MC_NAMES = {0:"ORANGE", 1:"GREEN", 2:"BLUE", 3:"YELLOW"}
_MC_CENTERS = [(1.2, 1.2), (0.8, 1.2), (0.8, 0.8), (1.2, 0.8)]

BAGUA_MBTI = {
    0: {"O": "ENFJ", "G": "INFJ", "B": "INTJ", "Y": "ENTJ"},
    1: {"O": "ENFP", "G": "INFP", "B": "INTP", "Y": "ENTP"},
    2: {"O": "ESFJ", "G": "ISFJ", "B": "ISTJ", "Y": "ESTJ"},
    3: {"O": "ESFP", "G": "ISFP", "B": "ISTP", "Y": "ESTP"},
    4: {"O": "ESTJ", "G": "ISTJ", "B": "ISFJ", "Y": "ESFJ"},
    5: {"O": "ESTP", "G": "ISTP", "B": "ISFP", "Y": "ESFP"},
    6: {"O": "ENTJ", "G": "INTJ", "B": "INFJ", "Y": "ENFJ"},
    7: {"O": "ENTP", "G": "INTP", "B": "INFP", "Y": "ENFP"},
}
COLOR_KEY = {_MC_ORANGE:"O", _MC_GREEN:"G", _MC_BLUE:"B", _MC_YELLOW:"Y"}

PERSONALITY_GROUPS = [
    ["ENFJ","INFJ","INTJ","ENTJ"],
    ["ENFP","INFP","INTP","ENTP"],
    ["ESFJ","ISFJ","ISTJ","ESTJ"],
    ["ESFP","ISFP","ISTP","ESTP"],
]

def _norm100_to_raw(v: float) -> float:
    if v <= 0: return 0.001
    return math.exp(v / 10.0)

def _calc_mind_color(ha, la, hb, lb, lg, hg):
    total_a = ha + la; total_b = hb + lb
    if total_a == 0: total_a = 0.001
    if total_b == 0: total_b = 0.001
    total_g = lg + hg
    r_ga = total_g / total_a
    r_gb = total_g / total_b
    best, dist = _MC_ORANGE, float("inf")
    for mc, (cx, cy) in enumerate(_MC_CENTERS):
        d = math.hypot(r_ga - cx, r_gb - cy)
        if d < dist:
            dist, best = d, mc
    return best

def _calc_bagua(la, ha, lb, hb, lg, hg, th, de):
    vals = [la+ha, lb+hb, lg+hg, th+de]
    dom = vals.index(max(vals))
    return [3, 0, 1, 2][dom]   # simplified

def _calc_personality(bagua, li_active, mind_color, beta_raw, theta_raw):
    row = BAGUA_MBTI.get(bagua, {})
    ck = COLOR_KEY.get(mind_color, "B")
    base = row.get(ck, "ISTP")
    if li_active:
        # theta > beta → flip I↔E
        flipped = ("E" if base[0]=="I" else "I") + base[1:]
        return flipped
    return base

def _calc_mbti_for_bands(bands):
    raw_la  = _norm100_to_raw(bands.get("low_alpha", 0))
    raw_ha  = _norm100_to_raw(bands.get("high_alpha", 0))
    raw_lb  = _norm100_to_raw(bands.get("low_beta", 0))
    raw_hb  = _norm100_to_raw(bands.get("high_beta", 0))
    raw_lg  = _norm100_to_raw(bands.get("low_gamma", 0))
    raw_hg  = _norm100_to_raw(bands.get("high_gamma", 0))
    raw_th  = _norm100_to_raw(bands.get("theta", 0))
    raw_de  = _norm100_to_raw(bands.get("delta", 0))
    raw_bet = _norm100_to_raw(bands.get("beta", 0))

    mc   = _calc_mind_color(raw_ha, raw_la, raw_hb, raw_lb, raw_lg, raw_hg)
    # Bagua based on dominant band group
    la_n = bands.get("low_alpha", 0); ha_n = bands.get("high_alpha", 0)
    lb_n = bands.get("low_beta", 0);  hb_n = bands.get("high_beta", 0)
    lg_n = bands.get("low_gamma", 0); hg_n = bands.get("high_gamma", 0)
    th_n = bands.get("theta", 0);     de_n = bands.get("delta", 0)
    bagua = _calc_bagua(la_n, ha_n, lb_n, hb_n, lg_n, hg_n, th_n, de_n)
    li_active = raw_th > raw_bet
    mbti = _calc_personality(bagua, li_active, mc, raw_bet, raw_th)
    return {
        "mind_color": _MC_NAMES[mc],
        "bagua": bagua,
        "li_active": li_active,
        "r_ga": round((raw_lg+raw_hg)/(raw_la+raw_ha), 3),
        "r_gb": round((raw_lg+raw_hg)/(raw_lb+raw_hb), 3),
        "theta_gt_beta": f"{bands.get('theta',0)} > {bands.get('beta',0)}",
        "mbti": mbti,
    }

# ── 查詢並分析三人 ────────────────────────────────────────
SESSIONS = [
    {"sid": 52, "name": "鄭小怡"},
    {"sid": 49, "name": "王筱琪"},
    {"sid": 48, "name": "紀羽珊"},
]

for item in SESSIONS:
    sid  = item["sid"]
    name = item["name"]
    rs   = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=15).json()
    bands = (rs.get("eeg_stats") or {}).get("bands_avg") or {}
    result = _calc_mbti_for_bands(bands)
    
    print(f"\n===== [{sid}] {name} =====")
    print(f"  腦波值 (0-100 正規化):")
    print(f"    alpha={bands.get('alpha')}  beta={bands.get('beta')}  theta={bands.get('theta')}  delta={bands.get('delta')}")
    print(f"    low_alpha={bands.get('low_alpha')}  high_alpha={bands.get('high_alpha')}")
    print(f"    low_beta={bands.get('low_beta')}   high_beta={bands.get('high_beta')}")
    print(f"    low_gamma={bands.get('low_gamma')}  high_gamma={bands.get('high_gamma')}")
    print(f"  決策路徑:")
    print(f"    Bagua       = {result['bagua']}")
    print(f"    MindColor   = {result['mind_color']}  (r_ga={result['r_ga']}, r_gb={result['r_gb']})")
    print(f"    li_active   = {result['li_active']}  (theta={bands.get('theta')} vs beta={bands.get('beta')})")
    print(f"  → MBTI = {result['mbti']}")
