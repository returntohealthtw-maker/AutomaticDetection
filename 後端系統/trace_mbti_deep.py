"""
完整追蹤：per-capture 的八卦 + MindColor 分佈，
解釋為何三人結果相同或不同。
"""
import sys, io, requests, urllib3, math
from scipy.stats import norm as _NORM_DIST

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

# ── 演算法常數（與 algorithms.py 完全一致）─────────────
LA_MEAN = -0.8718; LA_STD = 0.3506  # DATA_STATS["lowAlpha"]
BOUNDS  = [0, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 1.0]
BAGUA_NAME = {0:"乾(Qian)", 1:"兌(Dui)", 2:"離/震(Li/Zhen)",
              3:"巽(Xun)", 4:"坎(Kan)", 5:"艮(Gen)", 6:"坤(Kun)"}
_MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW = 0, 1, 2, 3
_MC_NAMES = {0:"ORANGE", 1:"GREEN", 2:"BLUE", 3:"YELLOW"}
_MC_CENTERS = {0:(120,120), 1:(80,120), 2:(80,80), 3:(120,80)}
PERSONALITY_GROUPS = [
    ["ENFJ","INFJ","INTJ","ENTJ"],
    ["ENFP","INFP","INTP","ENTP"],
    ["ESFJ","ISFJ","ISTJ","ESTJ"],
    ["ESFP","ISFP","ISTP","ESTP"],
]

def _norm100_to_raw(v):
    if v <= 0: return 0.001
    return math.exp(v / 10.0)

def _calc_mind_color(ha, la, hb, lb, lg, hg):
    alpha = ha + la; beta = hb + lb; gamma = lg + hg
    if alpha <= 0 or beta <= 0: return _MC_ORANGE
    f1 = gamma / alpha * 100
    f2 = gamma / beta  * 100
    best, dist = _MC_ORANGE, float("inf")
    for c, (cx, cy) in _MC_CENTERS.items():
        d = math.sqrt((cx-f1)**2 + (cy-f2)**2)
        if d < dist: dist, best = d, c
    return best

def _calc_mbti(bagua, li_active, mc, raw_beta, raw_th):
    if bagua == 0: return "ENTJ" if mc==_MC_GREEN else "ESTJ"
    if bagua == 1: return "ISFJ" if raw_beta>raw_th else "ISTJ"
    if bagua == 2:
        return ("ENFJ" if mc==_MC_BLUE else "ESFJ") if li_active else ("INFJ" if mc==_MC_BLUE else "INTJ")
    if bagua == 3: return "ESFP" if raw_beta>raw_th else "ESTP"
    if bagua == 4: return "INTP" if mc==_MC_GREEN else "ISTP"
    if bagua == 5: return "ENFP" if mc==_MC_BLUE else "ENTP"
    return "INFP" if mc==_MC_BLUE else "ISFP"  # bagua 6

def analyse_session(sid, name):
    rs = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=20).json()
    eeg = rs.get("eeg_stats", {})
    bands_avg = eeg.get("bands_avg", {})
    caps = eeg.get("bands_7") or []   # 可能有逐秒資料；若無則用 avg
    
    # 如果沒有 bands_7，用 bands_avg 模擬單一樣本
    if not caps:
        caps = [bands_avg]
    
    bagua_counter = {}; mc_counter = {}; mbti_counter = {}

    for c in caps:
        def g(k): return float(c.get(k, 0) or 0)
        la = g("low_alpha"); ha = g("high_alpha")
        lb = g("low_beta");  hb = g("high_beta")
        lg = g("low_gamma"); hg = g("high_gamma")
        th = g("theta"); be = g("beta") or (lb+hb)

        if la <= 0 or th <= 0: continue

        raw_la = _norm100_to_raw(la); raw_th = _norm100_to_raw(th)
        la_pct = float(_NORM_DIST.cdf((math.log10(max(raw_la,0.1)) - LA_MEAN) / LA_STD))
        th_pct = float(_NORM_DIST.cdf((math.log10(max(raw_th,0.1)) - LA_MEAN) / LA_STD))

        bagua = 6
        for i in range(6):
            if la_pct < BOUNDS[i+1]: bagua = i; break
        li_active = (bagua == 2 and th_pct > 0.5)

        raw_ha = _norm100_to_raw(ha) if ha>0 else 0
        raw_hb = _norm100_to_raw(hb) if hb>0 else 0
        raw_lb = _norm100_to_raw(lb) if lb>0 else 0
        raw_lg = _norm100_to_raw(lg) if lg>0 else 0
        raw_hg = _norm100_to_raw(hg) if hg>0 else 0
        mc = _calc_mind_color(raw_ha, raw_la, raw_hb, raw_lb, raw_lg, raw_hg)

        raw_beta = _norm100_to_raw(be) if be>0 else (raw_hb + raw_lb)
        mbti = _calc_mbti(bagua, li_active, mc, raw_beta, raw_th)

        bagua_counter[bagua] = bagua_counter.get(bagua, 0) + 1
        mc_counter[mc] = mc_counter.get(mc, 0) + 1
        mbti_counter[mbti] = mbti_counter.get(mbti, 0) + 1

    n = len(caps)
    print(f"\n===== [{sid}] {name}  (樣本數:{n}) =====")
    print(f"  bands_avg: la={bands_avg.get('low_alpha')} ha={bands_avg.get('high_alpha')} "
          f"lb={bands_avg.get('low_beta')} hb={bands_avg.get('high_beta')} "
          f"lg={bands_avg.get('low_gamma')} hg={bands_avg.get('high_gamma')} "
          f"th={bands_avg.get('theta')}")

    print(f"  八卦分佈:")
    for k in sorted(bagua_counter, key=lambda x: -bagua_counter[x]):
        pct = bagua_counter[k]*100//n
        print(f"    {BAGUA_NAME[k]:20s} {bagua_counter[k]:4d}筆 ({pct}%)")

    print(f"  MindColor 分佈:")
    for k in sorted(mc_counter, key=lambda x: -mc_counter[x]):
        pct = mc_counter[k]*100//n
        print(f"    {_MC_NAMES[k]:8s} {mc_counter[k]:4d}筆 ({pct}%)")

    print(f"  MBTI 分佈（群組評分前）:")
    for k in sorted(mbti_counter, key=lambda x: -mbti_counter[x]):
        pct = mbti_counter[k]*100//n
        print(f"    {k:6s} {mbti_counter[k]:4d}筆 ({pct}%)")

for item in [{"sid":52,"name":"鄭小怡"}, {"sid":49,"name":"王筱琪"}, {"sid":48,"name":"紀羽珊"}]:
    analyse_session(item["sid"], item["name"])
