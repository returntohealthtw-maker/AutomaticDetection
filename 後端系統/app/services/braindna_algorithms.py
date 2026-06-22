"""
BrainDNA 演算法核心模組
完全參照 BrainDNA-master/braindna/algorithms/brainwave.py 原始碼實作。

輸入：raw_arrays dict，結構：
  {
    "r_delta":  [<180 個 ThinkGear 原始功率值>],
    "r_theta":  [...],
    "r_lalpha": [...],   # lowAlpha
    "r_halpha": [...],   # highAlpha
    "r_lbeta":  [...],   # lowBeta
    "r_hbeta":  [...],   # highBeta
    "r_lgamma": [...],   # lowGamma
    "r_hgamma": [...],   # midGamma（BrainDNA 稱 midGamma）
    "attn":     [...],   # attention 0-100
    "medi":     [...],   # meditation 0-100
  }

輸出：各種腦波指標，與 BrainDNA 報告格式一致。
"""

import math
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# MindValueTop：各頻段原始值上限截斷（直接複製自 BrainDNA）
# ─────────────────────────────────────────────────────────────────────────────
CAP = {
    "r_delta":  98000,
    "r_theta":  98000,
    "r_lalpha": 50000,
    "r_halpha": 50000,
    "r_lbeta":  50000,
    "r_hbeta":  50000,
    "r_lgamma": 10000,
    "r_hgamma": 10000,
}

RAW_KEYS = ["r_delta", "r_theta", "r_lalpha", "r_halpha",
            "r_lbeta", "r_hbeta", "r_lgamma", "r_hgamma"]


def _clamp(v: float, cap: float) -> float:
    return max(0.0, min(float(v), cap))


def _proportion_range(value: float, level1: float, level2: float) -> float:
    """
    MindValueAlgorithm.proportionRange（直接複製自 BrainDNA 原始碼）。
    輸入原始佔比（0.0~1.0），映射到 0.0~1.0：
      ≤ level1 → (value/level1) × 0.5          （低半段 0~0.5）
      level1~level2 → (value-level1)/(level2-level1) × 0.5 + 0.5  （高半段 0.5~1.0）
      ≥ level2 → 1.0
    """
    if level1 > level2 or level1 < 0 or value <= 0:
        return 0.0
    if value >= level2:
        return 1.0
    if value <= level1:
        return (value / level1) * 0.5
    return (value - level1) / (level2 - level1) * 0.5 + 0.5


# proportionRange 各頻段標準範圍（來自 BrainDNA brainwave.py calcXxx 方法）
_PROP_RANGE = {
    "r_delta":  (0.60, 0.80),
    "r_theta":  (0.15, 0.30),
    "r_lalpha": (0.10, 0.20),
    "r_halpha": (0.10, 0.20),
    "r_lbeta":  (0.05, 0.10),
    "r_hbeta":  (0.05, 0.10),
    "r_lgamma": (0.03, 0.06),
    "r_hgamma": (0.03, 0.06),
}


# ─────────────────────────────────────────────────────────────────────────────
# Best 30-second window selection（與 BrainDNA evaluationReport.py 完全一致）
# 1. 把 N 秒資料切成每 30 秒一個視窗
# 2. 每個視窗計算 lowGamma 佔比，再 proportionRange 評分
# 3. 取得分最高的視窗（代表「腦波最佳狀態」）
# ─────────────────────────────────────────────────────────────────────────────
WINDOW_SIZE = 30   # 與 BrainDNA 一致


def _select_best_window(raw_arrays: Dict[str, List]) -> Dict[str, List]:
    """
    從 raw_arrays 中選出 lowGamma 佔比最佳的 30 秒視窗，
    回傳該視窗的 raw_arrays（結構相同，長度約 30）。
    若資料不足 30 秒，回傳原始資料。
    """
    n = len(raw_arrays.get("r_lalpha") or [])
    if n < WINDOW_SIZE:
        return raw_arrays  # 資料不足，用全部

    num_windows = n // WINDOW_SIZE  # BrainDNA 用整除，最後不足 30 的捨棄
    best_idx = 0
    best_score = -1.0

    for i in range(num_windows):
        start = i * WINDOW_SIZE
        end   = start + WINDOW_SIZE
        prop_sum = 0.0
        valid = 0
        for j in range(start, end):
            c = {k: _clamp(
                    (raw_arrays.get(k) or [])[j] if j < len(raw_arrays.get(k) or []) else 0.0,
                    CAP[k])
                 for k in RAW_KEYS}
            total = sum(c.values())
            if total > 0:
                prop_sum += c["r_lgamma"] / total
                valid += 1
        if valid > 0:
            score = _proportion_range(prop_sum / valid, 0.03, 0.06)
            if score > best_score:
                best_score = score
                best_idx = i

    start = best_idx * WINDOW_SIZE
    end   = start + WINDOW_SIZE
    result: Dict[str, List] = {}
    for k in list(RAW_KEYS) + ["attn", "medi"]:
        arr = raw_arrays.get(k) or []
        result[k] = arr[start:min(end, len(arr))]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MindValueCalcHelper（proportion 模式）
# 步驟零：選取 best 30-second window（evaluationReport.py maxArray）
# 步驟一：每秒截斷 → 八頻段總和 → 個別佔比 → 30 秒平均（0.0~1.0）
# 步驟二：proportionRange 正規化 → 映射到 0~1 → × 100 → 整數（0~100）
# 與 BrainDNA evaluationReport 的 *Strip 值完全一致。
# ─────────────────────────────────────────────────────────────────────────────
def calc_band_proportions(raw_arrays: Dict[str, List]) -> Optional[Dict[str, int]]:
    """
    輸入：raw_arrays（8 個頻段原始陣列，index 對齊，通常 180 秒）
    輸出：{ "low_alpha": int, "high_alpha": int, ... }
          值域 0-100，與 BrainDNA evaluationReport *Strip 值完全一致。
    步驟零：先選 best 30-second window（lowGamma 佔比最高）
    若資料不足（< 10 秒）回傳 None。
    """
    n = len(raw_arrays.get("r_lalpha") or [])
    if n < 10:
        return None
    # 若輸入已是 best window（由 compute_all 傳入），直接使用；
    # 若直接呼叫此函式（n >= 30），自動選 best window。
    if n >= WINDOW_SIZE * 2:
        raw_arrays = _select_best_window(raw_arrays)
        n = len(raw_arrays.get("r_lalpha") or [])

    prop_sum = {k: 0.0 for k in RAW_KEYS}
    valid = 0

    for i in range(n):
        # BrainDNA calcColumnSumArray：分母用「未截斷」原始值加總（完全對應原碼）
        # 分子才截斷（MindValueTop）；這讓 delta/theta 的龐大原始值壓低 beta/gamma 佔比
        raw_row = {k: float((raw_arrays.get(k) or [0])[i]
                            if i < len(raw_arrays.get(k) or []) else 0)
                   for k in RAW_KEYS}
        uncapped_total = sum(raw_row.values())   # 未截斷總和 → 分母
        if uncapped_total <= 0:
            continue
        for k in RAW_KEYS:
            capped = _clamp(raw_row[k], CAP[k])  # 截斷 → 分子
            prop_sum[k] += capped / uncapped_total
        valid += 1

    if valid == 0:
        return None

    def _norm(k: str) -> int:
        raw_prop = prop_sum[k] / valid          # 步驟一：原始佔比 0.0~1.0
        l1, l2 = _PROP_RANGE[k]
        return round(_proportion_range(raw_prop, l1, l2) * 100)   # 步驟二

    return {
        "delta":      _norm("r_delta"),
        "theta":      _norm("r_theta"),
        "low_alpha":  _norm("r_lalpha"),
        "high_alpha": _norm("r_halpha"),
        "low_beta":   _norm("r_lbeta"),
        "high_beta":  _norm("r_hbeta"),
        "low_gamma":  _norm("r_lgamma"),
        "high_gamma": _norm("r_hgamma"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MindStressAlgorithm
# 使用 lowAlpha 和 midGamma 原始陣列，直接算壓力分數 0-100
# ─────────────────────────────────────────────────────────────────────────────
_STRESS_MG_BOTTOM  = 2000
_STRESS_MG_TOP     = 6000
_STRESS_LA_BOTTOM  = 4000
_STRESS_LA_TOP     = 25000


def _calc_ave_clamped(arr: List, bottom: float, top: float) -> float:
    if not arr:
        return 0.0
    total = sum(max(bottom, min(top, v)) for v in arr)
    return total / len(arr)


def _calc_percent(value: float, bottom: float, top: float) -> float:
    if top <= bottom:
        return 0.0
    return max(0.0, min(1.0, (value - bottom) / (top - bottom)))


def calc_stress_score(raw_arrays: Dict[str, List]) -> int:
    """
    MindStressAlgorithm：使用 lowAlpha（r_lalpha）和 midGamma（r_hgamma）原始陣列。
    回傳 0-100 壓力分數。
    """
    mid_gamma = raw_arrays.get("r_hgamma") or []
    low_alpha = raw_arrays.get("r_lalpha") or []
    if not mid_gamma or not low_alpha:
        return 50

    ave_mg = _calc_ave_clamped(mid_gamma, _STRESS_MG_BOTTOM, _STRESS_MG_TOP)
    ave_la = _calc_ave_clamped(low_alpha, _STRESS_LA_BOTTOM, _STRESS_LA_TOP)
    pt_mg  = _calc_percent(ave_mg, _STRESS_MG_BOTTOM, _STRESS_MG_TOP)
    pt_la  = _calc_percent(ave_la, _STRESS_LA_BOTTOM, _STRESS_LA_TOP)
    return int(50 * pt_mg + 50 * pt_la)


# ─────────────────────────────────────────────────────────────────────────────
# MindColorAlgorithm：腦色（橙/綠/藍/黃）
# 使用各頻段原始平均值，計算 gamma/alpha 和 gamma/beta 比值
# ─────────────────────────────────────────────────────────────────────────────
ORANGE = 0
GREEN  = 1
BLUE   = 2
YELLOW = 3

_COLOR_CENTERS = {
    "orange": (32.5, 42.5),
    "green":  (32.5, 27.5),
    "blue":   (42.5, 52.5),
    "yellow": (25.0, 20.0),
}
_COLOR_TYPES = {"orange": ORANGE, "green": GREEN, "blue": BLUE, "yellow": YELLOW}


def _arr_mean(arr: List) -> float:
    return sum(arr) / len(arr) if arr else 0.0


def calc_mind_color(raw_arrays: Dict[str, List]) -> int:
    """
    MindColorAlgorithm：回傳 0=橙, 1=綠, 2=藍, 3=黃
    """
    ha = _arr_mean(raw_arrays.get("r_halpha") or [])
    la = _arr_mean(raw_arrays.get("r_lalpha") or [])
    hb = _arr_mean(raw_arrays.get("r_hbeta")  or [])
    lb = _arr_mean(raw_arrays.get("r_lbeta")  or [])
    lg = _arr_mean(raw_arrays.get("r_lgamma") or [])
    mg = _arr_mean(raw_arrays.get("r_hgamma") or [])

    alpha = ha + la
    beta  = hb + lb
    gamma = lg + mg
    if alpha <= 0 or beta <= 0:
        return ORANGE

    f1 = (gamma / alpha) * 100
    f2 = (gamma / beta)  * 100

    min_dist = float("inf")
    best = "orange"
    for name, (cx, cy) in _COLOR_CENTERS.items():
        d = math.sqrt((cx - f1) ** 2 + (cy - f2) ** 2)
        if d < min_dist:
            min_dist = d
            best = name
    return _COLOR_TYPES[best]


# ─────────────────────────────────────────────────────────────────────────────
# MindBalanceAlgorithm：平衡分數（使用 attention/meditation 0-100 陣列）
# ─────────────────────────────────────────────────────────────────────────────
def _calc_zone(arr: List[int], thresholds: List[int]) -> List[int]:
    zone = [0] * (len(thresholds) - 1)
    for v in arr:
        for j in range(1, len(thresholds)):
            if thresholds[j - 1] <= v <= thresholds[j]:
                zone[j - 1] += 1
                break
    return zone


def calc_mind_balance(attn: List[int], medi: List[int]) -> int:
    """MindBalanceAlgorithm：回傳 0-100"""
    if not attn or not medi:
        return 50
    z_attn = _calc_zone(attn, [0, 40, 70, 100])
    z_medi = _calc_zone(medi, [0, 40, 70, 100])
    f1 = math.fabs((z_attn[1] + z_attn[2]) - (z_medi[1] + z_medi[2]))
    f2 = math.fabs(z_attn[0] - z_medi[0]) + math.fabs(z_attn[1] - z_medi[1]) + math.fabs(z_attn[2] - z_medi[2])
    f3 = z_attn[2] + z_medi[2]
    v  = (30.0 - f1) / 30 * 100 * 0.3
    v += (60.0 - f2) / 60 * 100 * 0.5
    v += f3 / 60.0 * 100 * 0.2
    return max(0, min(100, int(v)))


# ─────────────────────────────────────────────────────────────────────────────
# MindEnergyAlgorithm：活力分數（使用 attention/meditation 0-100 陣列）
# ─────────────────────────────────────────────────────────────────────────────
def calc_mind_energy(attn: List[int], medi: List[int]) -> int:
    """MindEnergyAlgorithm：回傳 0-100"""
    if not attn or not medi:
        return 50
    z_attn = _calc_zone(attn, [0, 40, 70, 100])
    z_medi = _calc_zone(medi, [0, 40, 70, 100])
    f1 = z_attn[2] + z_medi[2]
    t  = z_attn[0] + z_attn[1] + z_attn[2]
    tm = z_medi[0] + z_medi[1] + z_medi[2]
    f2 = 100 * ((z_attn[0] / t if t else 0) + (z_medi[0] / tm if tm else 0))
    v  = f1 / 60.0 * 100 * 0.5
    v += (100 - f2 * 0.5) * 0.5
    return max(0, min(100, int(v)))


# ─────────────────────────────────────────────────────────────────────────────
# 總入口：從 raw_arrays 計算全部 BrainDNA 指標
# ─────────────────────────────────────────────────────────────────────────────
def compute_all(raw_arrays: Dict[str, List]) -> Dict:
    """
    輸入 raw_arrays，回傳完整的 BrainDNA 指標字典。
    完全對應 BrainDNA evaluationReport.py 的資料流：

      mindColor  → report.calcColor(mindArray)     ← 全部 6 個視窗投票
      maxArray   → calcBand(mindArray)              ← best 30-second window
      bands      → helper.calcXxx(maxArray)         ← best 30s
      stress     → MindStressAlgorithm(maxArray)    ← best 30s
      balance    → MindBalanceAlgorithm(maxArray)   ← best 30s attention/medi
      energy     → MindEnergyAlgorithm(maxArray)    ← best 30s attention/medi
    """
    n = len(raw_arrays.get("r_lalpha") or [])
    if n < 10:
        return {"valid": False}

    # best 30-second window（一次選取，傳給所有需要 best window 的算法）
    best_win = _select_best_window(raw_arrays)

    attn = [max(0, min(100, int(v))) for v in (best_win.get("attn") or [])]
    medi = [max(0, min(100, int(v))) for v in (best_win.get("medi") or [])]

    # bands：傳入 best_win 直接計算，避免 _select_best_window 被重複呼叫
    bands = calc_band_proportions(best_win)
    if bands is None:
        return {"valid": False}

    stress  = calc_stress_score(best_win)
    balance = calc_mind_balance(attn, medi)
    energy  = calc_mind_energy(attn, medi)
    color   = calc_mind_color(raw_arrays)
    # overall_score：對應 BrainDNA evaluationReport.py 的整體分數公式
    overall = int(balance * 0.6 + energy * 0.2 + (100 - stress) * 0.2 + 0.5)

    return {
        "valid":         True,
        "bands":         bands,
        "stress":        stress,
        "balance":       balance,
        "energy":        energy,
        "color":         color,
        "overall_score": max(0, min(100, overall)),
    }
