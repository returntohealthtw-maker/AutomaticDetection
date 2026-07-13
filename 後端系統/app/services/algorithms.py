"""
腦波演算法計算引擎
依據設計文件 01_演算法整理與修正.md 及 07_SDK資料需求與後端演算法.md
"""
from dataclasses import dataclass
from typing import List, Optional
import math

from scipy.stats import norm as _NORM

from app.algorithms.data_stats import DATA_STATS
from app.algorithms.bagua import Bagua
from app.algorithms.mbti import Personality


@dataclass
class EegBands:
    """一秒的腦波頻帶數值"""
    delta:      float
    theta:      float
    low_alpha:  float
    high_alpha: float
    low_beta:   float
    high_beta:  float
    low_gamma:  float
    high_gamma: float
    attention:  float
    meditation: float
    good_signal: int = 0

    @property
    def alpha(self) -> float:
        return self.low_alpha + self.high_alpha

    @property
    def beta(self) -> float:
        return self.low_beta + self.high_beta

    @property
    def gamma(self) -> float:
        return self.low_gamma + self.high_gamma

    @property
    def total(self) -> float:
        return (self.delta + self.theta + self.alpha +
                self.beta + self.gamma)

    @property
    def non_delta_total(self) -> float:
        return self.total - self.delta


@dataclass
class BandAverages:
    """整場檢測的頻帶平均值"""
    delta:      float
    theta:      float
    low_alpha:  float
    high_alpha: float
    low_beta:   float
    high_beta:  float
    low_gamma:  float
    high_gamma: float
    attention:  float
    meditation: float
    sample_count: int

    @property
    def alpha(self):  return self.low_alpha + self.high_alpha
    @property
    def beta(self):   return self.low_beta + self.high_beta
    @property
    def gamma(self):  return self.low_gamma + self.high_gamma
    @property
    def total(self):  return self.delta + self.alpha + self.beta + self.gamma + self.theta


def compute_averages(captures: List[dict]) -> BandAverages:
    """
    從原始擷取資料計算各頻帶平均值
    captures: list of EegCapture dict（排除訊號不良的資料）
    """
    valid = [c for c in captures if c.get("good_signal", 1) == 0]
    if not valid:
        valid = captures  # 若全部訊號不良，使用全部資料

    n = len(valid)
    if n == 0:
        return BandAverages(0,0,0,0,0,0,0,0,0,0,0)

    def avg(key): return sum(c.get(key, 0) for c in valid) / n

    return BandAverages(
        delta      = avg("delta"),
        theta      = avg("theta"),
        low_alpha  = avg("low_alpha"),
        high_alpha = avg("high_alpha"),
        low_beta   = avg("low_beta"),
        high_beta  = avg("high_beta"),
        low_gamma  = avg("low_gamma"),
        high_gamma = avg("high_gamma"),
        attention  = avg("attention"),
        meditation = avg("meditation"),
        sample_count = n
    )


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """安全除法，避免除以零"""
    return a / b if b > 1e-10 else default


def _clamp(val: float, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, val))


def compute_all_indices(avg: BandAverages) -> dict:
    """
    計算全部 30 個腦波指標
    回傳 dict：{指標名稱: {"value": float, "pct": float, "category": str}}
    """
    d = avg.delta
    t = avg.theta
    la = avg.low_alpha
    ha = avg.high_alpha
    lb = avg.low_beta
    hb = avg.high_beta
    lg = avg.low_gamma
    hg = avg.high_gamma
    a  = avg.alpha
    b  = avg.beta
    g  = avg.gamma
    att = avg.attention
    med = avg.meditation
    total = avg.total if avg.total > 0 else 1.0

    results = {}

    # ── 認知能力類 ──────────────────────────────────────────────
    # CCR 認知清晰度：Alpha / (Beta + Theta)
    results["CCR"] = {
        "value": _safe_div(a, b + t),
        "category": "cognitive",
        "label": "認知清晰度"
    }
    # SRR 壓力回復力：Alpha / Beta
    results["SRR"] = {
        "value": _safe_div(a, b),
        "category": "cognitive",
        "label": "壓力回復力"
    }
    # EBI 執行腦力指數：Beta / (Alpha + Theta)
    results["EBI"] = {
        "value": _safe_div(b, a + t),
        "category": "cognitive",
        "label": "執行腦力指數"
    }
    # IQ 直覺商數：Theta / (Alpha + Beta)
    results["IQ_EEG"] = {
        "value": _safe_div(t, a + b),
        "category": "cognitive",
        "label": "直覺商數"
    }
    # LBR 邏輯腦比率：Low Beta / Beta
    results["LBR"] = {
        "value": _safe_div(lb, b) * 100,
        "category": "cognitive",
        "label": "邏輯分析比率"
    }
    # HBR 執行腦比率：High Beta / Beta
    results["HBR"] = {
        "value": _safe_div(hb, b) * 100,
        "category": "cognitive",
        "label": "執行力比率"
    }
    # ATT 專注力
    results["ATT"] = {
        "value": att,
        "category": "cognitive",
        "label": "專注力"
    }
    # FCI 前額葉控制指數：(Alpha + Beta) / (Delta + Theta)
    results["FCI"] = {
        "value": _safe_div(a + b, d + t),
        "category": "cognitive",
        "label": "前額葉控制指數"
    }

    # ── 壓力與放鬆類 ─────────────────────────────────────────────
    # SI 壓力指數：(Beta + Delta) / Alpha
    results["SI"] = {
        "value": _safe_div(b + d, a),
        "category": "stress",
        "label": "壓力指數"
    }
    # MED 冥想放鬆指數
    results["MED"] = {
        "value": med,
        "category": "stress",
        "label": "放鬆指數"
    }
    # ABI Alpha 主導指數：Alpha / Total
    results["ABI"] = {
        "value": _safe_div(a, total) * 100,
        "category": "stress",
        "label": "Alpha 主導指數"
    }
    # SQI 睡眠品質指數：Delta / Total
    results["SQI"] = {
        "value": _safe_div(d, total) * 100,
        "category": "stress",
        "label": "睡眠品質指數"
    }
    # FAI 疲勞指數：(Delta + Theta) / (Alpha + Beta)
    results["FAI"] = {
        "value": _safe_div(d + t, a + b),
        "category": "stress",
        "label": "疲勞指數"
    }
    # RSI 靜息穩定指數：Low Alpha / High Alpha
    results["RSI"] = {
        "value": _safe_div(la, ha),
        "category": "stress",
        "label": "靜息穩定指數"
    }

    # ── 情緒與性格類 ─────────────────────────────────────────────
    # EI 情緒穩定性：Alpha / (Beta + Delta)
    results["EI"] = {
        "value": _safe_div(a, b + d),
        "category": "emotional",
        "label": "情緒穩定性"
    }
    # EQ 情緒商數：(Alpha + Theta) / Beta
    results["EQ"] = {
        "value": _safe_div(a + t, b),
        "category": "emotional",
        "label": "情緒商數"
    }
    # INS 直覺感受力：Theta / Total
    results["INS"] = {
        "value": _safe_div(t, total) * 100,
        "category": "emotional",
        "label": "直覺感受力"
    }
    # EMO 情感連結力：Low Gamma / Total
    results["EMO"] = {
        "value": _safe_div(lg, total) * 100,
        "category": "emotional",
        "label": "情感連結力（慈悲）"
    }
    # INN 內在安定感：Low Alpha / Total
    results["INN"] = {
        "value": _safe_div(la, total) * 100,
        "category": "emotional",
        "label": "內在安定感"
    }
    # VIT 生命活力感：High Alpha / Total
    results["VIT"] = {
        "value": _safe_div(ha, total) * 100,
        "category": "emotional",
        "label": "生命活力感（氣血）"
    }

    # ── 人際互動類 ───────────────────────────────────────────────
    # SOC 社交敏感度：Gamma / (Alpha + Beta)
    results["SOC"] = {
        "value": _safe_div(g, a + b),
        "category": "social",
        "label": "社交敏感度"
    }
    # OBS 環境觀察力：High Gamma / Total
    results["OBS"] = {
        "value": _safe_div(hg, total) * 100,
        "category": "social",
        "label": "環境觀察力"
    }
    # EMP 同理共鳴力：(Theta + Low Gamma) / Total
    results["EMP"] = {
        "value": _safe_div(t + lg, total) * 100,
        "category": "social",
        "label": "同理共鳴力"
    }
    # COM 溝通表達力：Beta / (Theta + Delta)
    results["COM"] = {
        "value": _safe_div(b, t + d),
        "category": "social",
        "label": "溝通表達力"
    }

    # ── 領導力類 ─────────────────────────────────────────────────
    # LDR 領導力指數：(Beta + Gamma) / (Delta + Theta)
    results["LDR"] = {
        "value": _safe_div(b + g, d + t),
        "category": "leadership",
        "label": "領導力指數"
    }
    # DEC 決策力指數：High Beta / (Low Beta + Alpha)
    results["DEC"] = {
        "value": _safe_div(hb, lb + a),
        "category": "leadership",
        "label": "決策力指數"
    }
    # VIS 願景思維力：Theta / Beta
    results["VIS"] = {
        "value": _safe_div(t, b),
        "category": "leadership",
        "label": "願景思維力"
    }
    # RES 抗壓韌性：Alpha / (Beta + Delta + Theta)
    results["RES"] = {
        "value": _safe_div(a, b + d + t),
        "category": "leadership",
        "label": "抗壓韌性"
    }
    # CRE 創造力指數：Theta / Alpha
    results["CRE"] = {
        "value": _safe_div(t, a),
        "category": "leadership",
        "label": "創造力指數"
    }
    # FOC 高度聚焦力：High Beta / Total
    results["FOC"] = {
        "value": _safe_div(hb, total) * 100,
        "category": "leadership",
        "label": "高度聚焦力"
    }

    # ── 轉換為 0~100 百分比（Sigmoid 正規化）──────────────────────
    for key in results:
        raw = results[key]["value"]
        # 已是百分比的指標直接 clamp
        if key in ("LBR","HBR","ATT","MED","ABI","SQI","FAI","INS",
                   "EMO","INN","VIT","OBS","EMP","FOC"):
            results[key]["pct"] = round(_clamp(raw, 0, 100), 1)
        else:
            # Sigmoid 正規化：將比率映射到 0~100
            # sigmoid(x) = 1/(1+e^(-k*(x-1)))，以 ratio=1 為中心
            k = 3.0
            sig = 1.0 / (1.0 + math.exp(-k * (raw - 1.0)))
            results[key]["pct"] = round(sig * 100, 1)

    return results


def _norm100_to_raw(v: float) -> float:
    """
    還原 Android bandTo100() 正規化：
        bandTo100(raw) = log10(raw + 1) / 6.0 * 100
        → raw = 10^(v * 0.06) − 1
    DB 的 low_alpha / theta 等欄位存的是 0-100 正規化值，
    Bagua.calcBagua / getPersonalityFromBagua 需要原始 ThinkGear 值（~萬為單位）。
    """
    v = max(0.01, float(v))
    return (10.0 ** (v * 0.06)) - 1.0


def compute_mbti(avg: BandAverages) -> dict:
    """
    使用 BrainDNA 原始八卦演算法計算 MBTI（移植自 BrainDNA/braindna/algorithms/）：

        1. bandTo100 反函數還原 DB 的 0-100 值 → 原始 ThinkGear 值
        2. Bagua.calcBagua(lowAlpha)          → 八卦（7 型，乾兌震巽坎艮坤）
        3. Personality.getPersonalityFromBagua(bagua, theta)  → MBTI 16 型
        4. 顯示分數從 laPct / thPct 推導（方向與型別字母一致）

    與前端 _etComputeMBTILayers 原型層完全相同的演算流程。
    """
    # 1. 還原 raw ThinkGear 值
    raw_la = _norm100_to_raw(avg.low_alpha)
    raw_th = _norm100_to_raw(avg.theta)

    # 2. 八卦（8 卦系統含離卦，與前端 _etBaguaMBTI(useLi=True) 完全一致）
    #    laPct 0.250~0.375 帶：theta_p > 0.5 → 離卦(INFJ/INFP)，否則震卦(ENFJ/ENFP)
    bagua = Bagua.calcBaguaWithLi(raw_la, raw_th)

    # 3. MBTI 16 型
    personality = Personality.getPersonalityFromBagua(bagua, raw_th)
    mbti_type   = personality.id

    # 4. 顯示用百分位分數（從 laPct / thPct 推導，方向與 mbti_type 一致）
    LA_MEAN = DATA_STATS["lowAlpha"]["mean"]
    LA_STD  = DATA_STATS["lowAlpha"]["std"]
    la_pct  = float(_NORM.cdf((math.log10(max(raw_la, 0.1)) - LA_MEAN) / LA_STD))
    th_pct  = float(_NORM.cdf((math.log10(max(raw_th, 0.1)) - LA_MEAN) / LA_STD))

    # E/I：段內位置（7 段，每段 0.125，交替 I/E）
    seg     = min(int(la_pct / 0.125), 6)
    seg_pos = (la_pct - seg * 0.125) / 0.125
    ei_str  = _clamp(seg_pos * 45 + 5, 5, 50)
    ei_pct  = (50 + ei_str) if mbti_type[0] == 'E' else (50 - ei_str)

    # N/S：laPct 與 0.375 邊界距離（< 0.375 = N 型卦組，>= 0.375 = S 型卦組）
    ns_dist = ((0.375 - la_pct) / 0.375) if la_pct < 0.375 else ((la_pct - 0.375) / 0.625)
    ns_base = _clamp(50 + ns_dist * 45, 50, 95)
    ns_pct  = ns_base if mbti_type[1] == 'N' else (100 - ns_base)

    # T/F & J/P：theta 百分位強度（遠離 0.5 → 信號越強）
    tf_str = _clamp(abs(th_pct - 0.5) * 80 + 10, 10, 45)
    tf_pct = (50 + tf_str) if mbti_type[2] == 'T' else (50 - tf_str)
    jp_str = _clamp(abs(th_pct - 0.5) * 70 + 10, 10, 45)
    jp_pct = (50 + jp_str) if mbti_type[3] == 'J' else (50 - jp_str)

    return {
        "mbti_type":  mbti_type,
        "ei_score":   round(ei_pct, 1),
        "ns_score":   round(ns_pct, 1),
        "tf_score":   round(tf_pct, 1),
        "jp_score":   round(jp_pct, 1),
        "ei_label":   mbti_type[0],
        "ns_label":   mbti_type[1],
        "tf_label":   mbti_type[2],
        "jp_label":   mbti_type[3],
        "confidence": round(
            (abs(ei_pct-50) + abs(ns_pct-50) + abs(tf_pct-50) + abs(jp_pct-50)) / 2, 1
        ),
        "secondary":  None,
    }


def compute_mbti_v6(avg: BandAverages) -> dict:
    """
    MBTI v6.0 直接競爭演算法（取代八卦中間層，直接從腦波計算4軸）

    文獻根據：
    - E/I：Matthews & Gilliland (1999) — α↑最可靠內向指標；γ↑/Focus外向激活
    - N/S：Rao & Singhania (2013) — θ與DMN直覺相關；β↓精確當下感知
    - T/F：Miller & Cohen (2001) — β邏輯；Gallese (2001) — γ↓共情鏡像神經
    - J/P：Miller & Cohen (2001) — β↑/Focus前額葉執行閉合；θ/放鬆靈活探索

    輸入：BandAverages（attention=focus，meditation=relaxation，其餘同名）
    輸出：{mbti_type, ei_score, ns_score, tf_score, jp_score,
           eiDiff, nsDiff, tfDiff, jpDiff, secondaries}
    """
    theta      = float(avg.theta)
    highAlpha  = float(avg.high_alpha)
    lowAlpha   = float(avg.low_alpha)
    lowBeta    = float(avg.low_beta)
    highBeta   = float(avg.high_beta)
    highGamma  = float(avg.high_gamma)
    lowGamma   = float(avg.low_gamma)
    focus      = float(avg.attention)     # attention → focus
    relaxation = float(avg.meditation)    # meditation → relaxation

    # STEP 1: 4-axis direct competition
    E_score = focus * 0.35 + highGamma * 0.35 + highBeta * 0.30
    I_score = highAlpha * 0.40 + relaxation * 0.30 + lowAlpha * 0.30
    eiDiff  = E_score - I_score

    N_score = theta * 0.60 + highAlpha * 0.40
    S_score = lowBeta * 0.55 + highGamma * 0.45
    nsDiff  = N_score - S_score   # N if > +8 (全球 S≈73% 修正)

    T_score = lowBeta * 0.50 + highBeta * 0.50
    F_score = lowGamma * 0.55 + highAlpha * 0.45
    tfDiff  = T_score - F_score

    J_score = highBeta * 0.45 + focus * 0.55
    P_score = theta * 0.50 + relaxation * 0.50
    jpDiff  = J_score - P_score

    # STEP 2: Determine type letters
    ei = 'E' if eiDiff > 0 else 'I'
    ns = 'N' if nsDiff > 8 else 'S'
    tf = 'T' if tfDiff > 0 else 'F'
    jp = 'J' if jpDiff > 0 else 'P'
    mbti_type = ei + ns + tf + jp

    # STEP 3: 4-axis scores (0-99, 50=boundary)
    def clamp(v: float) -> int:
        return max(5, min(99, round(v)))

    ei_score = clamp(50 + eiDiff * 0.6)
    ns_score = clamp(50 + (nsDiff - 8) * 0.6)
    tf_score = clamp(50 + tfDiff * 0.6)
    jp_score = clamp(50 + jpDiff * 0.6)

    # STEP 4: Secondary personalities (max 2, based on axis boundary distance)
    def clamp78(v: float) -> int:
        return max(10, min(78, round(v)))

    axis_borders = [
        {'axis': 'EI', 'diff': abs(eiDiff),     'pos': 0, 'flip': 'I' if ei == 'E' else 'E'},
        {'axis': 'NS', 'diff': abs(nsDiff - 8),  'pos': 1, 'flip': 'S' if ns == 'N' else 'N'},
        {'axis': 'TF', 'diff': abs(tfDiff),      'pos': 2, 'flip': 'F' if tf == 'T' else 'T'},
        {'axis': 'JP', 'diff': abs(jpDiff),      'pos': 3, 'flip': 'P' if jp == 'J' else 'J'},
    ]
    axis_borders.sort(key=lambda x: x['diff'])

    secondaries = []
    for border in axis_borders[:2]:
        strength = clamp78(78 - border['diff'] * 1.8)
        if strength < 20:
            break
        sec_chars = list(mbti_type)
        sec_chars[border['pos']] = border['flip']
        secondaries.append({
            'mbti':     ''.join(sec_chars),
            'strength': strength,
            'axis':     border['axis'],
            'reason':   f"{border['axis']}軸邊界（腦波差距 {border['diff']:.1f}）",
        })

    return {
        'mbti_type':   mbti_type,
        'type':        mbti_type,
        'ei_score':    ei_score,
        'ns_score':    ns_score,
        'tf_score':    tf_score,
        'jp_score':    jp_score,
        'ei_label':    ei,
        'ns_label':    ns,
        'tf_label':    tf,
        'jp_label':    jp,
        'eiDiff':      round(eiDiff, 2),
        'nsDiff':      round(nsDiff, 2),
        'tfDiff':      round(tfDiff, 2),
        'jpDiff':      round(jpDiff, 2),
        'confidence':  round(
            (abs(ei_score - 50) + abs(ns_score - 50) +
             abs(tf_score - 50) + abs(jp_score - 50)) / 2, 1
        ),
        'secondaries': secondaries,
        'secondary':   secondaries[0]['mbti'] if secondaries else None,
    }


def _bagua_mbti_from_pct(la_pct: float, th_pct: float) -> dict:
    """
    Bagua MBTI directly from 0-1 percentiles (skips log-normalization).
    Used for non-lowAlpha/theta band pairs so each value is treated as a
    relative percentile (val/100) of its own distribution.
    """
    BOUNDS = [0, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 1.0]
    _BAGUA_NAMES = ["乾","兌","離/震","巽","坎","艮","坤"]

    la_pct = max(0.001, min(0.999, la_pct))
    th_pct = max(0.001, min(0.999, th_pct))

    bagua = 6
    for i in range(6):
        if la_pct < BOUNDS[i + 1]:
            bagua = i
            break

    high = th_pct > 0.5
    li_active = bagua == 2 and high

    MAP = [
        ("INTJ", "INTP"),
        ("ENTJ", "ENTP"),
        ("INFJ", "INFP") if li_active else ("ENFJ", "ENFP"),
        ("ISTJ", "ISFJ"),
        ("ESTJ", "ESFJ"),
        ("ISTP", "ISFP"),
        ("ESTP", "ESFP"),
    ]
    primary = MAP[bagua][0 if high else 1]

    zone_start = BOUNDS[bagua]
    zone_end   = BOUNDS[bagua + 1]
    zone_half  = (zone_end - zone_start) / 2
    dist       = min(la_pct - zone_start, zone_end - la_pct)
    la_conf    = min(1.0, dist / zone_half) if zone_half else 0
    th_conf    = min(1.0, abs(th_pct - 0.5) / 0.3)
    confidence = round((la_conf * 0.65 + th_conf * 0.35) * 100)

    secondary = None
    if la_conf < 0.6:
        closer_lower = (la_pct - zone_start) < (zone_end - la_pct)
        adj = bagua - 1 if closer_lower else bagua + 1
        if 0 <= adj <= 6:
            adj_li = adj == 2 and high
            adj_map = ("INFJ", "INFP") if adj_li else MAP[adj]
            alt = adj_map[0 if high else 1]
            if alt != primary:
                secondary = alt
    if not secondary:
        alt = MAP[bagua][1 if high else 0]
        if alt != primary:
            secondary = alt

    bagua_obj = Bagua.calcBaguaWithLi(
        _norm100_to_raw(la_pct * 100), _norm100_to_raw(th_pct * 100)
    )
    return {
        "type":       primary,
        "secondary":  secondary,
        "confidence": confidence,
        "la_pct":     la_pct,
        "th_pct":     th_pct,
        "bagua":      bagua_obj.id,
        "bagua_name": bagua_obj.name,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 原始 BrainDNA MindColor + Group-Scoring 演算法
# 來源：BrainDNA-master/braindna/algorithms/brainwave.py & MBTIPersonality.py
# ──────────────────────────────────────────────────────────────────────────────

_MC_ORANGE = 0
_MC_GREEN  = 1
_MC_BLUE   = 2
_MC_YELLOW = 3

_MC_CENTERS = {
    _MC_ORANGE: (32.5, 42.5),
    _MC_GREEN:  (32.5, 27.5),
    _MC_BLUE:   (42.5, 52.5),
    _MC_YELLOW: (25.0, 20.0),
}

# 原始 personalityGroups：同組的四種型別互相影響（群組評分機制的基礎）
PERSONALITY_GROUPS: list = [
    ["INFP", "ISFP", "ENFJ", "ESFJ"],  # Group 0 – 共感型
    ["ESFP", "ESTP", "ISTJ", "ISFJ"],  # Group 1 – 感知型
    ["ISTP", "INTP", "ENTJ", "ESTJ"],  # Group 2 – 理性型
    ["ENTP", "ENFP", "INFJ", "INTJ"],  # Group 3 – 直覺型
]


def _calc_mind_color(ha: float, la: float, hb: float, lb: float,
                     lg: float, hg: float) -> int:
    """
    原始 BrainDNA MindColorAlgorithm.calc()。
    輸入為 0-100 正規化值（highAlpha, lowAlpha, highBeta, lowBeta, lowGamma, highGamma）。
    傳回 _MC_ORANGE/GREEN/BLUE/YELLOW (0-3)。
    """
    alpha = ha + la
    beta  = hb + lb
    gamma = lg + hg
    if alpha <= 0 or beta <= 0:
        return _MC_ORANGE
    f1 = gamma / alpha * 100   # gamma/alpha ratio × 100
    f2 = gamma / beta  * 100   # gamma/beta  ratio × 100
    best_color = _MC_ORANGE
    min_dist   = float("inf")
    for c, (cx, cy) in _MC_CENTERS.items():
        d = math.sqrt((cx - f1) ** 2 + (cy - f2) ** 2)
        if d < min_dist:
            min_dist   = d
            best_color = c
    return best_color


def _calc_personality_from_bagua_color(bagua: int, li_active: bool,
                                        mind_color: int,
                                        beta_norm: float,
                                        theta_norm: float) -> str:
    """
    原始 BrainDNA Personality.calcPersonality()：
    (卦位, 心靈色彩, beta, theta) → MBTI 字串。

    大多數卦位用「心靈色彩」（GREEN/BLUE）區分兩個子型；
    兌(1)/巽(3) 用 beta > theta 區分。
    """
    if bagua == 0:   # 乾: GREEN→ENTJ, else→ESTJ
        return "ENTJ" if mind_color == _MC_GREEN else "ESTJ"
    elif bagua == 1:  # 兌: beta>theta→ISFJ, else→ISTJ
        return "ISFJ" if beta_norm > theta_norm else "ISTJ"
    elif bagua == 2:  # 離(li_active) / 震(not li_active)
        if li_active:
            return "ENFJ" if mind_color == _MC_BLUE else "ESFJ"
        else:
            return "INFJ" if mind_color == _MC_BLUE else "INTJ"
    elif bagua == 3:  # 巽: beta>theta→ESFP, else→ESTP
        return "ESFP" if beta_norm > theta_norm else "ESTP"
    elif bagua == 4:  # 坎: GREEN→INTP, else→ISTP
        return "INTP" if mind_color == _MC_GREEN else "ISTP"
    elif bagua == 5:  # 艮: BLUE→ENFP, else→ENTP
        return "ENFP" if mind_color == _MC_BLUE else "ENTP"
    else:             # 坤(6): BLUE→INFP, else→ISFP
        return "INFP" if mind_color == _MC_BLUE else "ISFP"


def compute_mbti_group_scoring(captures: list) -> list | None:
    """
    原始 BrainDNA calculateMBTIGroup 群組評分演算法：

    對每筆 capture 計算 (卦位 + 心靈色彩) → 單一 MBTI，
    然後進行群組累積：主型 +2 分，同組其他三型各 +1 分。

    即使所有時間窗都算出同一型別（如 ISTJ），
    也能自然產生 ISTJ(40%) + ESFP(20%) + ESTP(20%) + ISFJ(20%) 的分布。

    傳回 [{type, pct, layers}, ...] 或 None（資料不足）。
    """
    LA_MEAN = DATA_STATS["lowAlpha"]["mean"]
    LA_STD  = DATA_STATS["lowAlpha"]["std"]
    BOUNDS  = [0, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 1.0]

    # 初始化分數表（16 種型別均為 0）
    scores: dict[str, float] = {t: 0.0 for grp in PERSONALITY_GROUPS for t in grp}

    def _get(c, key):
        v = c.get(key, 0) if isinstance(c, dict) else getattr(c, key, 0)
        return float(v or 0)

    valid = 0
    first_type: str | None = None

    for c in captures:
        la = _get(c, "low_alpha")
        th = _get(c, "theta")
        if la <= 0 or th <= 0:
            continue

        raw_la = _norm100_to_raw(la)
        raw_th = _norm100_to_raw(th)
        la_pct = float(_NORM.cdf((math.log10(max(raw_la, 0.1)) - LA_MEAN) / LA_STD))
        th_pct = float(_NORM.cdf((math.log10(max(raw_th, 0.1)) - LA_MEAN) / LA_STD))

        bagua = 6
        for i in range(6):
            if la_pct < BOUNDS[i + 1]:
                bagua = i
                break
        li_active = (bagua == 2 and th_pct > 0.5)

        ha = _get(c, "high_alpha")
        hb = _get(c, "high_beta")
        lb = _get(c, "low_beta")
        lg = _get(c, "low_gamma")
        hg = _get(c, "high_gamma")

        # MindColor 必須用原始值計算（歸一化值的 gamma/alpha 比值不在正常範圍）
        raw_ha = _norm100_to_raw(ha) if ha > 0 else 0.0
        raw_hb = _norm100_to_raw(hb) if hb > 0 else 0.0
        raw_lb = _norm100_to_raw(lb) if lb > 0 else 0.0
        raw_lg = _norm100_to_raw(lg) if lg > 0 else 0.0
        raw_hg = _norm100_to_raw(hg) if hg > 0 else 0.0
        mind_color = _calc_mind_color(raw_ha, raw_la, raw_hb, raw_lb, raw_lg, raw_hg)

        # 兌/巽 的 beta vs theta 比較也使用原始值（正規化後比例關係失真）
        raw_beta = raw_hb + raw_lb
        mbti_type  = _calc_personality_from_bagua_color(
            bagua, li_active, mind_color, raw_beta, raw_th
        )

        # 群組評分：主型 +2，同組其他 +1
        for grp in PERSONALITY_GROUPS:
            if mbti_type in grp:
                for t in grp:
                    scores[t] += 2 if t == mbti_type else 1
                break

        valid += 1
        if first_type is None:
            first_type = mbti_type

    if valid == 0 or first_type is None:
        return None

    # 只保留有得分的型別，依分數排序
    total = sum(scores.values())
    if total == 0:
        return None

    sorted_items = sorted(
        [(t, scores[t]) for t in scores if scores[t] > 0],
        key=lambda x: x[1], reverse=True
    )

    # 轉換為百分比（整數），確保總和 = 100
    pcts = [(t, max(1, round(s * 100 / total))) for t, s in sorted_items]
    diff = 100 - sum(p for _, p in pcts)
    if pcts:
        pcts[0] = (pcts[0][0], pcts[0][1] + diff)

    return [{"type": t, "pct": p, "layers": ["群組評分"]} for t, p in pcts]


def _bagua_mbti_from_raw(raw_la: float, raw_th: float) -> dict:
    """與前端 _etBaguaMBTI(rawLA, rawTH, useLi=True) 完全一致。"""
    LA_MEAN = DATA_STATS["lowAlpha"]["mean"]
    LA_STD  = DATA_STATS["lowAlpha"]["std"]
    BOUNDS  = [0, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 1.0]

    la_pct = float(_NORM.cdf((math.log10(max(raw_la, 0.1)) - LA_MEAN) / LA_STD)) if raw_la > 0 else 0.4
    bagua  = 6
    for i in range(6):
        if la_pct < BOUNDS[i + 1]:
            bagua = i
            break

    th_pct = float(_NORM.cdf((math.log10(max(raw_th, 0.1)) - LA_MEAN) / LA_STD)) if raw_th > 0 else 0.4
    high   = th_pct > 0.5
    li_active = bagua == 2 and high

    MAP = [
        ("INTJ", "INTP"),
        ("ENTJ", "ENTP"),
        ("INFJ", "INFP") if li_active else ("ENFJ", "ENFP"),
        ("ISTJ", "ISFJ"),
        ("ESTJ", "ESFJ"),
        ("ISTP", "ISFP"),
        ("ESTP", "ESFP"),
    ]
    primary = MAP[bagua][0 if high else 1]

    zone_start = BOUNDS[bagua]
    zone_end   = BOUNDS[bagua + 1]
    zone_half  = (zone_end - zone_start) / 2
    dist       = min(la_pct - zone_start, zone_end - la_pct)
    la_conf    = min(1.0, dist / zone_half) if zone_half else 0
    th_conf    = min(1.0, abs(th_pct - 0.5) / 0.3)
    confidence = round((la_conf * 0.65 + th_conf * 0.35) * 100)

    secondary = None
    if la_conf < 0.6:
        closer_lower = (la_pct - zone_start) < (zone_end - la_pct)
        adj = bagua - 1 if closer_lower else bagua + 1
        if 0 <= adj <= 6:
            adj_li = adj == 2 and high
            adj_map = ("INFJ", "INFP") if adj_li else MAP[adj]
            alt = adj_map[0 if high else 1]
            if alt != primary:
                secondary = alt
    # Always compute the theta-flip type as fallback secondary (same bagua zone,
    # opposite theta half).  This ensures every report has at least one secondary
    # to display, mirroring the APP's 4-layer multi-personality behaviour.
    if not secondary:
        alt = MAP[bagua][1 if high else 0]
        if alt != primary:
            secondary = alt

    bagua_obj = Bagua.calcBaguaWithLi(raw_la, raw_th)
    return {
        "type": primary,
        "secondary": secondary,
        "confidence": confidence,
        "la_pct": la_pct,
        "th_pct": th_pct,
        "bagua": bagua_obj.id,
        "bagua_name": bagua_obj.name,
    }


def _mbti_layer_from_raw_arrays(r_la: list, r_th: list) -> dict:
    if len(r_la) < 1 or len(r_th) < 1:
        return {}
    raw_la = sum(r_la) / len(r_la)
    raw_th = sum(r_th) / len(r_th)
    br = _bagua_mbti_from_raw(raw_la, raw_th)
    mbti_type = br["type"]
    la_pct, th_pct = br["la_pct"], br["th_pct"]

    seg     = min(int(la_pct / 0.125), 6)
    seg_pos = (la_pct - seg * 0.125) / 0.125
    ei_str  = _clamp(seg_pos * 45 + 5, 5, 50)
    ei_pct  = (50 + ei_str) if mbti_type[0] == "E" else (50 - ei_str)

    ns_dist = ((0.375 - la_pct) / 0.375) if la_pct < 0.375 else ((la_pct - 0.375) / 0.625)
    ns_base = _clamp(50 + ns_dist * 45, 50, 95)
    ns_pct  = ns_base if mbti_type[1] == "N" else (100 - ns_base)

    tf_str = _clamp(abs(th_pct - 0.5) * 80 + 10, 10, 45)
    tf_pct = (50 + tf_str) if mbti_type[2] == "T" else (50 - tf_str)
    jp_str = _clamp(abs(th_pct - 0.5) * 70 + 10, 10, 45)
    jp_pct = (50 + jp_str) if mbti_type[3] == "J" else (50 - jp_str)

    return {
        "type": mbti_type,
        "secondary": br["secondary"],
        "confidence": br["confidence"],
        "bagua": br["bagua"],
        "bagua_name": br["bagua_name"],
        "ei_score": round(ei_pct, 1),
        "ns_score": round(ns_pct, 1),
        "tf_score": round(tf_pct, 1),
        "jp_score": round(jp_pct, 1),
    }


def _mbti_contradiction(a: str, b: str) -> int:
    """MBTI 矛盾距離（Hamming distance，0-4），每個不同維度各計 1 分。"""
    if not a or not b or len(a) < 4 or len(b) < 4:
        return 0
    return sum(a[i] != b[i] for i in range(4))


def compute_window_mbtis(raw_arrays: dict) -> list:
    """
    BrainDNA 原始算法：每 30 秒視窗各自計算一個 MBTI（狀態性格樣本）。

    對應 BrainDNA reports.py 的 reportMBTI()：
    - 每段取 lowAlpha 均值 → calcBagua → getPersonalityFromBagua(theta)
    - 腦色用 MindColor 原始算法（gamma/alpha, gamma/beta 距離）
    - 最終用 calcPersonality(bagua, color, theta, beta)

    回傳 list of dict，每個 dict:
        { type, window_idx, la_mean, th_mean, color, bagua_int }
    """
    WINDOW = 30
    LA_MEAN = DATA_STATS["lowAlpha"]["mean"]
    LA_STD  = DATA_STATS["lowAlpha"]["std"]
    BOUNDS  = [0, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 1.0]

    def _arr(key):
        return [float(v) for v in (raw_arrays.get(key) or []) if v]

    r_la = _arr("r_lalpha")
    r_th = _arr("r_theta")
    r_ha = _arr("r_halpha")
    r_hb = _arr("r_hbeta")
    r_lb = _arr("r_lbeta")
    r_lg = _arr("r_lgamma")
    r_hg = _arr("r_hgamma")

    n = len(r_la)
    if n < WINDOW or not r_th:
        return []

    num_windows = n // WINDOW
    results = []

    for wi in range(num_windows):
        s, e = wi * WINDOW, (wi + 1) * WINDOW

        def _seg_mean(arr):
            seg = arr[s:min(e, len(arr))]
            return sum(seg) / len(seg) if seg else 0.0

        raw_la = _seg_mean(r_la)
        raw_th = _seg_mean(r_th)
        raw_ha = _seg_mean(r_ha)
        raw_hb = _seg_mean(r_hb)
        raw_lb = _seg_mean(r_lb)
        raw_lg = _seg_mean(r_lg)
        raw_hg = _seg_mean(r_hg)

        if raw_la <= 0 or raw_th <= 0:
            continue

        # 卦位（7 卦，不含離卦，與 BrainDNA calcBagua 一致）
        la_pct = float(_NORM.cdf((math.log10(max(raw_la, 0.1)) - LA_MEAN) / LA_STD))
        bagua_int = 6
        for i in range(6):
            if la_pct < BOUNDS[i + 1]:
                bagua_int = i
                break

        # 腦色（原始 gamma/alpha, gamma/beta 距離）
        color = _calc_mind_color(raw_ha, raw_la, raw_hb, raw_lb, raw_lg, raw_hg)

        # 兌(1)/巽(3) 用 beta vs theta 分兩型
        raw_beta = raw_hb + raw_lb
        mbti_type = _calc_personality_from_bagua_color(
            bagua_int, False, color, raw_beta, raw_th
        )

        results.append({
            "type":       mbti_type,
            "window_idx": wi,
            "la_mean":    raw_la,
            "th_mean":    raw_th,
            "color":      color,
            "bagua_int":  bagua_int,
        })

    return results


def assign_personality_layers(archetype_type: str, window_mbtis: list) -> dict:
    """
    依矛盾距離（Hamming distance）把視窗 MBTI 分配到四層：

      peer     → 與 archetype 矛盾最小（最接近本我，無需偽裝）
      family   → 與 archetype 矛盾最大（訓練最深的討好性格）
      social   → 矛盾程度介於 peer 與 family 之間

    若所有視窗 MBTI 相同（全等於 archetype），四層均相同。
    若視窗不足，以 archetype 填位。
    """
    if not window_mbtis:
        return {}

    types_with_idx = [(w["type"], w["window_idx"]) for w in window_mbtis]
    scores = [(t, _mbti_contradiction(archetype_type, t), idx)
              for t, idx in types_with_idx]

    # peer = 矛盾最小（同分時取最早視窗）
    peer_entry = min(scores, key=lambda x: (x[1], x[2]))
    # family = 矛盾最大（同分時取最晚視窗，深層穩定態）
    family_entry = max(scores, key=lambda x: (x[1], -x[2]))

    peer_score   = peer_entry[1]
    family_score = family_entry[1]
    mid_target   = (peer_score + family_score) / 2

    # social = 剩餘中矛盾分最接近中點的視窗
    remaining = [s for s in scores
                 if s[2] != peer_entry[2] and s[2] != family_entry[2]]
    if remaining:
        social_entry = min(remaining, key=lambda x: abs(x[1] - mid_target))
    else:
        # peer/family 同一視窗（資料只有 1 段）→ social = archetype
        social_entry = (archetype_type, 0, -1)

    def _build(t: str) -> dict:
        return _mbti_layer_from_raw_arrays([], []) if not t else {
            "type":       t,
            "secondary":  None,
            "confidence": 70,
        }

    return {
        "peer":   _build(peer_entry[0]),
        "family": _build(family_entry[0]),
        "social": _build(social_entry[0]),
        # 矛盾分數供報告第二章使用
        "_contradiction": {
            "peer":   peer_entry[1],
            "family": family_entry[1],
            "social": abs(social_entry[1] - mid_target) if remaining else 0,
        },
    }


def compute_mbti_layers_from_captures(captures: list, raw_arrays: dict = None) -> dict:
    """
    四層 MBTI 地圖（BrainDNA 矛盾距離分配算法）。

    優先使用 raw_arrays（30 秒視窗 × 腦色 × 八卦，與 BrainDNA 原始一致）。
    無 raw_arrays 時，退回 captures 均值計算原型，並將四層均設為原型。

    四層含義：
      archetype  天生本質（全段均值，未受環境訓練）
      peer       同儕關係（與原型矛盾最小，最接近真我）
      social     社會化  （矛盾介於同儕與原生之間）
      family     原生家庭（與原型矛盾最大，訓練最深的討好性格）
    """
    def _get(c, key):
        v = c.get(key, 0) if isinstance(c, dict) else getattr(c, key, 0)
        return float(v or 0)

    # ── Archetype：全段 lowAlpha + theta 均值 → 八卦 → MBTI ──────────────────
    if raw_arrays:
        r_la = [float(v) for v in (raw_arrays.get("r_lalpha") or []) if v]
        r_th = [float(v) for v in (raw_arrays.get("r_theta")  or []) if v]
    else:
        r_la = [_norm100_to_raw(_get(c, "low_alpha")) for c in captures if _get(c, "low_alpha") > 0]
        r_th = [_norm100_to_raw(_get(c, "theta"))     for c in captures if _get(c, "theta")     > 0]

    if len(r_la) < 4 or len(r_th) < 4:
        fb = compute_mbti(compute_averages(captures)) if captures else {"mbti_type": "INTP", "type": "INTP"}
        fb = {**fb, "type": fb.get("type") or fb.get("mbti_type", "INTP")}
        return {"archetype": fb, "family": fb, "social": fb, "peer": fb,
                "_source": "fallback"}

    archetype = _mbti_layer_from_raw_arrays(r_la, r_th)
    archetype_type = archetype.get("type") or "INTP"

    # ── 30 秒視窗 MBTI 樣本 ─────────────────────────────────────────────────
    if raw_arrays:
        window_mbtis = compute_window_mbtis(raw_arrays)
    else:
        # 沒有 raw_arrays：把 captures 每 30 筆視為一個視窗
        window_mbtis = []
        for wi in range(len(captures) // 30):
            seg = captures[wi*30:(wi+1)*30]
            seg_la = [_norm100_to_raw(_get(c, "low_alpha")) for c in seg if _get(c, "low_alpha") > 0]
            seg_th = [_norm100_to_raw(_get(c, "theta"))     for c in seg if _get(c, "theta")     > 0]
            if seg_la and seg_th:
                r = _mbti_layer_from_raw_arrays(seg_la, seg_th)
                window_mbtis.append({"type": r.get("type", archetype_type), "window_idx": wi,
                                     "la_mean": sum(seg_la)/len(seg_la),
                                     "th_mean": sum(seg_th)/len(seg_th), "color": 0, "bagua_int": 0})

    # ── 矛盾距離分配 ────────────────────────────────────────────────────────
    if window_mbtis:
        layers = assign_personality_layers(archetype_type, window_mbtis)
    else:
        layers = {}

    def _layer(key: str) -> dict:
        if layers.get(key):
            return layers[key]
        return {**archetype}  # fallback to archetype

    return {
        "archetype": archetype,
        "peer":      _layer("peer"),
        "social":    _layer("social"),
        "family":    _layer("family"),
        "_contradiction": layers.get("_contradiction", {}),
        "_source": "window_contradiction" if window_mbtis else "fallback",
    }


def aggregate_mbti_profiles(layers: dict) -> list:
    """與前端 _renderEthrMbtiAnalysis 聚合邏輯一致，回傳 [{type, pct, layers}, ...]。"""
    layer_order = ["archetype", "family", "social", "peer"]
    type_score  = {}
    type_layers = {}

    for key in layer_order:
        lay = layers.get(key) or {}
        mbti_type = lay.get("type") or lay.get("mbti_type")
        if not mbti_type:
            continue
        conf = lay.get("confidence", 70) or 70
        primary_prob   = 50 + conf / 2
        secondary_prob = 100 - primary_prob

        type_score[mbti_type] = type_score.get(mbti_type, 0) + primary_prob / 4
        type_layers.setdefault(mbti_type, [])
        if key not in type_layers[mbti_type]:
            type_layers[mbti_type].append(key)

        secondary = lay.get("secondary")
        if secondary:
            type_score[secondary] = type_score.get(secondary, 0) + secondary_prob / 4

    sorted_profiles = sorted(
        [(t, round(s)) for t, s in type_score.items() if s >= 5],
        key=lambda x: x[1],
        reverse=True,
    )
    total = sum(p for _, p in sorted_profiles)
    if total and total != 100 and sorted_profiles:
        top = list(sorted_profiles[0])
        top[1] += 100 - total
        sorted_profiles[0] = tuple(top)

    return [
        {"type": t, "pct": p, "layers": type_layers.get(t, [])}
        for t, p in sorted_profiles
    ]


def build_mbti_payload(avg: BandAverages, captures: list = None,
                       raw_arrays: dict = None) -> dict:
    """
    產出報告 App / headless 共用的 MBTI 欄位。

    v6.0：使用直接競爭演算法，不再依賴八卦中間層。
    主性格、4軸分數、次性格全部由 compute_mbti_v6() 計算。
    """
    v6 = compute_mbti_v6(avg)
    mbti_type  = v6['mbti_type']
    secondaries = [
        {
            "mbti":     s['mbti'],
            "strength": s['strength'],
            "reason":   s.get('reason', f"{s.get('axis','')}軸邊界特質"),
        }
        for s in v6.get('secondaries', [])
    ]

    return {
        "mbti_primary":      mbti_type,
        "mbti_ei":           v6['ei_score'],
        "mbti_ns":           v6['ns_score'],
        "mbti_tf":           v6['tf_score'],
        "mbti_jp":           v6['jp_score'],
        "mbti_ei_diff":      v6['eiDiff'],
        "mbti_ns_diff":      v6['nsDiff'],
        "mbti_tf_diff":      v6['tfDiff'],
        "mbti_jp_diff":      v6['jpDiff'],
        "mbti_bagua":        "",
        "mbti_bagua_name":   "",
        "mbti_secondaries":  secondaries,
        "mbti_profiles":     [{"type": mbti_type, "pct": 100, "layers": ["v6"]}],
        "mbti_layers":       None,
    }
