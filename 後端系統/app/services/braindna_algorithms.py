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
    # 依據實測裝置原始值校正（成人均值：delta~506K, theta~104K, lgamma~11K, hgamma~8K）
    # 原始值比 BrainDNA 設計假設（delta~50K）高 5~10 倍，需同比放大 CAP
    "r_delta":  500_000,
    "r_theta":  200_000,
    "r_lalpha":  50_000,
    "r_halpha":  50_000,
    "r_lbeta":   50_000,
    "r_hbeta":   50_000,
    "r_lgamma":  25_000,
    "r_hgamma":  20_000,
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


# proportionRange 各頻段閾值（依 17 筆實測資料重新校正，2026-07-13）
# level1 = p50（中位數）→ 得分 50 分的基準線
# level2 = 觀測最大值 × 1.3（預留 30% 空間，確保不輕易滿分）
# 實測分佈（17 sessions）：
#   Delta  39.8~54.4%  p50=47.2%  max=54.4% → level2=54.4*1.3≈70% (用60%較合理)
#   Theta  11.3~20.0%  p50=14.7%  max=20.0% → level2=20.0*1.3=26%
#   Low α   2.4~6.2%   p50= 4.1%  max= 6.2% → level2= 6.2*1.3= 8%
#   High α  1.7~6.4%   p50= 3.4%  max= 6.4% → level2= 6.4*1.3= 8%
#   Low β   1.5~4.3%   p50= 3.0%  max= 4.3% → level2= 4.3*1.3= 6%
#   High β  2.6~8.0%   p50= 4.1%  max= 8.0% → level2= 8.0*1.3=10%
#   Low γ   1.1~5.1%   p50= 2.8%  max= 5.1% → level2= 5.1*1.3= 7%
#   High γ  0.7~4.3%   p50= 2.0%  max= 4.3% → level2= 4.3*1.3= 6%
_PROP_RANGE = {
    "r_delta":  (0.47, 0.60),    # p50=47.2%，level2 保留寬裕
    "r_theta":  (0.14, 0.26),    # p50=14.7%，level2 從 19%→26%（修正滿分問題）
    "r_lalpha": (0.040, 0.080),  # p50= 4.1%，level2 從 6.5%→8%
    "r_halpha": (0.033, 0.080),  # p50= 3.4%，level2 從 6.0%→8%（修正滿分問題）
    "r_lbeta":  (0.028, 0.060),  # p50= 3.0%，level2 從 5.5%→6%
    "r_hbeta":  (0.041, 0.100),  # p50= 4.1%，level1 從 5.0%→4.1%
    "r_lgamma": (0.028, 0.070),  # p50= 2.8%，level1 從 3.3%→2.8%
    "r_hgamma": (0.020, 0.060),  # p50= 2.0%，level2 略調
}


# ─────────────────────────────────────────────────────────────────────────────
# Best 30-second window selection（與 BrainDNA evaluationReport.py 完全一致）
# 1. 把 N 秒資料切成每 30 秒一個視窗
# 2. 每個視窗計算 lowGamma 佔比，再 proportionRange 評分
# 3. 取得分最高的視窗（代表「腦波最佳狀態」）
# ─────────────────────────────────────────────────────────────────────────────
WINDOW_SIZE = 30   # 與 BrainDNA 一致

# 信號品質下限（供 calc_band_proportions 及 MBTI 計算共用）
# delta < 30K = 電極接觸不良（族群均值 ~198K，30K ≈ 15%）
# 這類秒數的 beta/gamma 比例因分母過小而虛高，應排除
# ⚠ 此值僅適用於原始 ThinkGear 值；對 bandTo100(0~100) 輸入會全部過濾
#   → 自動偵測模式：見 _detect_input_scale()
MIN_DELTA_QUALITY: int = 30_000


def _detect_input_scale(raw_arrays: Dict[str, List]) -> str:
    """
    自動偵測 raw_arrays 的數值尺度：
    - 'raw'     : 原始 ThinkGear 值（任一頻段 > 1,000，通常 delta 可達 10,000~500,000）
    - 'norm100' : bandTo100 正規化值（全部頻段 ≤ 1,000）
    - 'unknown' : 資料不足無法判斷

    判斷規則：取所有 8 個頻段的最大值（不只看 r_delta，避免 5-band 裝置 r_delta=0 誤判）
      any_band > 1000  → raw（原始 ThinkGear 輸出）
      all_bands ≤ 1000 → norm100（bandTo100、BLE 或 5-band 裝置輸出）
    """
    overall_max = 0.0
    for k in RAW_KEYS:
        arr = raw_arrays.get(k) or []
        if arr:
            band_max = max((float(v) for v in arr if v), default=0.0)
            if band_max > overall_max:
                overall_max = band_max
    if overall_max == 0.0:
        return "unknown"
    if overall_max > 1000:
        return "raw"
    return "norm100"

# ─────────────────────────────────────────────────────────────────────────────
# 兒童專用 CAP 值與 proportionRange 閾值（report_type='child' 時使用）
#
# 設計依據：
#   1. Springer Nature 2025（450名健康兒童）：3歲清醒兒童
#      delta 佔相對功率 39~49%，theta ~25%，gamma ~2%
#   2. BrainDNA 成人 CAP（delta=98K）在兒童 delta 均值 826K 下只截到 12%，
#      嚴重失真。需提高 CAP 讓比例回到文獻水平。
#   3. CAP 計算方式：目標佔比 × 觀測未截斷總和（929K）
#      delta: 0.44 × 929K ≈ 400K | theta: 0.25 × 929K ≈ 230K
#      lgamma/hgamma: 0.02 × 929K ≈ 20K（原 10K）
#   4. proportionRange 閾值根據正確 CAP 後的實際比例設計，
#      讓正常活躍兒童落在 58~83 區間（有層次分佈、不均一）
# ⚠ 目前基於單一兒童樣本（Session #63，3歲），須以更多兒童資料持續校準
# ─────────────────────────────────────────────────────────────────────────────
CHILD_CAP: Dict[str, int] = {
    "r_delta":  400_000,   # 成人: 98K  | 兒童均值: ~826K → 提高至 400K
    "r_theta":  230_000,   # 成人: 98K  | 兒童均值: ~167K → 提高至 230K
    "r_lalpha":  50_000,   # 不變（兒童 lalpha 均值 34K，未超過 cap）
    "r_halpha":  50_000,
    "r_lbeta":   50_000,
    "r_hbeta":   50_000,
    "r_lgamma":  20_000,   # 成人: 10K  | 兒童均值: ~42K → 提高至 20K
    "r_hgamma":  20_000,   # 成人: 10K  | 兒童均值: ~17K → 提高至 20K
}

CHILD_PROP_RANGE: Dict[str, tuple] = {
    # key: (level1, level2) — 兒童以正確 CAP 計算後的實際佔比區間
    "r_delta":  (0.35, 0.55),   # 文獻: 39~49% | 觀測(新CAP): ~44.6% → 74分
    "r_theta":  (0.08, 0.22),   # 文獻: ~25%   | 觀測(新CAP): ~12.3% → 66分
    "r_lalpha": (0.015, 0.060), # 文獻: ~7.5%  | 觀測(新CAP): ~2.4%  → 60分
    "r_halpha": (0.015, 0.060), # 文獻: ~7.5%  | 觀測(新CAP): ~2.2%  → 58分
    "r_lbeta":  (0.010, 0.040), # 文獻: ~4%    | 觀測(新CAP): ~1.7%  → 62分
    "r_hbeta":  (0.020, 0.070), # 文獻: ~4%    | 觀測(新CAP): ~5.3%  → 83分
    "r_lgamma": (0.015, 0.040), # 文獻: ~2%    | 觀測(新CAP): ~3.1%  → 82分
    "r_hgamma": (0.010, 0.030), # 文獻: ~2%    | 觀測(新CAP): ~1.8%  → 70分
}


BDNA_GOOD_SIGNAL_THRESHOLD = 50  # 與 qEEG pipeline 一致：ThinkGear good_signal < 50 = 乾淨秒


def _filter_bad_signal_epochs(raw_arrays: Dict[str, List]) -> Dict[str, List]:
    """
    根據 r_good_signal（ThinkGear 訊號品質）過濾壞秒。

    過濾規則（與 qEEG pipeline 一致）：
      good_signal < 50  → 乾淨秒，保留
      good_signal >= 50 → 壞秒（電極接觸不良 / 肌電干擾），排除

    若無 r_good_signal 資料（空陣列或全 0），原樣回傳（不過濾）。
    注意：Android raw 路徑已有 delta < 30,000 過濾；
          此函式主要補 WebApp bandTo100 路徑的過濾邏輯。
    """
    gs = raw_arrays.get("r_good_signal") or []
    if not gs or not any(v > 0 for v in gs):
        return raw_arrays  # 無 good_signal 資料，不過濾

    all_keys = list(RAW_KEYS) + ["attn", "medi", "r_good_signal"]
    n = len(gs)

    keep_idx = [i for i in range(n) if i < len(gs) and int(gs[i]) < BDNA_GOOD_SIGNAL_THRESHOLD]
    if not keep_idx:
        return raw_arrays  # 全都是壞秒，保守起見回傳原始資料

    filtered: Dict[str, List] = {}
    for k in all_keys:
        arr = raw_arrays.get(k) or []
        filtered[k] = [arr[i] for i in keep_idx if i < len(arr)]

    return filtered


def _select_best_window(raw_arrays: Dict[str, List], cap: Optional[Dict] = None,
                        pr_table: Optional[Dict] = None) -> Dict[str, List]:
    """
    從 raw_arrays 中選出 lowGamma 佔比最佳的 30 秒視窗，
    回傳該視窗的 raw_arrays（結構相同，長度約 30）。
    若資料不足 30 秒，回傳原始資料。

    與 BrainDNA evaluationReport.py 完全一致：
    - 每 30 秒一個視窗，最後不足 30 秒的部分視窗也納入比較
    - 分母用「未截斷」原始值總和（calcColumnSumArray 行為）
    - 分子用截斷後 lowGamma，再 proportionRange 評分
    """
    n = len(raw_arrays.get("r_lalpha") or [])
    if n < WINDOW_SIZE:
        return raw_arrays  # 資料不足，用全部

    active_cap = cap if cap is not None else CAP
    active_pr = pr_table if pr_table is not None else _PROP_RANGE
    lgamma_cap = active_cap.get("r_lgamma", CAP["r_lgamma"])
    pr_l1, pr_l2 = active_pr.get("r_lgamma", _PROP_RANGE["r_lgamma"])

    # BrainDNA evaluationReport.py 第 36 行：`if len(tmpArr) > 0: mindArray.append(tmpArr)`
    # 最後不足 30 秒的部分視窗也納入
    num_windows = math.ceil(n / WINDOW_SIZE)
    best_idx = 0
    best_score = -1.0

    for i in range(num_windows):
        start = i * WINDOW_SIZE
        end   = min(start + WINDOW_SIZE, n)  # 最後視窗可能短於 30 秒
        prop_sum = 0.0
        valid = 0
        for j in range(start, end):
            # 分母：uncapped 原始值之和（與 BrainDNA calcColumnSumArray 一致）
            raw_row = {k: float((raw_arrays.get(k) or [])[j]
                                if j < len(raw_arrays.get(k) or []) else 0.0)
                       for k in RAW_KEYS}
            uncapped_total = sum(raw_row.values())
            if uncapped_total > 0:
                # 分子：capped lowGamma（使用 active_cap）
                prop_sum += _clamp(raw_row["r_lgamma"], lgamma_cap) / uncapped_total
                valid += 1
        if valid > 0:
            score = _proportion_range(prop_sum / valid, pr_l1, pr_l2)
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
def calc_band_proportions(raw_arrays: Dict[str, List], is_child: bool = False,
                          _scale: str = "") -> Optional[Dict[str, int]]:
    """
    輸入：raw_arrays（8 個頻段原始陣列，index 對齊，通常 180 秒）
    輸出：{ "low_alpha": int, "high_alpha": int, ... }
          值域 0-100，與 BrainDNA evaluationReport *Strip 值完全一致。
    步驟零：先選 best 30-second window（lowGamma 佔比最高）
    若資料不足（< 10 秒）回傳 None。

    自動偵測輸入尺度：
    - 'raw'     原始 ThinkGear 值 → 使用 MIN_DELTA_QUALITY=30,000 品質過濾
    - 'norm100' bandTo100 值      → 品質門檻降至 0（不過濾）, CAP 縮放至 100
    """
    n = len(raw_arrays.get("r_lalpha") or [])
    if n < 10:
        return None

    # 自動偵測輸入尺度（若呼叫端已傳入 _scale 則直接使用，避免重複運算）
    scale = _scale or _detect_input_scale(raw_arrays)

    if scale == "norm100":
        # bandTo100 輸入：CAP 縮放為 100，不套用 delta 品質門檻
        # 比例計算邏輯與 raw 完全相同，只是數值尺度不同
        active_cap = {k: 100 for k in CAP}
        min_delta_q = 0.0  # 不過濾（bandTo100 delta 最大只有 100）
    else:
        # 兒童使用較高的 CAP 值，讓 delta/theta 比例回到文獻水平
        active_cap = CHILD_CAP if is_child else CAP
        min_delta_q = float(MIN_DELTA_QUALITY)

    # 若輸入已是 best window（由 compute_all 傳入），直接使用；
    # 若直接呼叫此函式（n >= 30），自動選 best window。
    if n >= WINDOW_SIZE * 2:
        raw_arrays = _select_best_window(
            raw_arrays, cap=active_cap,
            pr_table=CHILD_PROP_RANGE if is_child else _PROP_RANGE)
        n = len(raw_arrays.get("r_lalpha") or [])

    prop_sum = {k: 0.0 for k in RAW_KEYS}
    valid = 0

    for i in range(n):
        # BrainDNA calcColumnSumArray：分母用「未截斷」原始值加總（完全對應原碼）
        # 分子才截斷（MindValueTop）；這讓 delta/theta 的龐大原始值壓低 beta/gamma 佔比
        raw_row = {k: float((raw_arrays.get(k) or [0])[i]
                            if i < len(raw_arrays.get(k) or []) else 0)
                   for k in RAW_KEYS}
        uncapped_total = sum(raw_row.values())   # 未截斷總和 → 分母（永遠不截斷）
        if uncapped_total <= 0:
            continue
        # 電極接觸品質過濾（僅 raw 模式有效；norm100 模式 min_delta_q=0）
        if raw_row["r_delta"] < min_delta_q:
            continue
        for k in RAW_KEYS:
            capped = _clamp(raw_row[k], active_cap[k])  # 截斷 → 分子
            prop_sum[k] += capped / uncapped_total
        valid += 1

    if valid == 0:
        return None

    prop_range_table = CHILD_PROP_RANGE if is_child else _PROP_RANGE

    def _norm(k: str) -> int:
        raw_prop = prop_sum[k] / valid          # 步驟一：原始佔比 0.0~1.0
        l1, l2 = prop_range_table[k]
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
# 完全對應 BrainDNA MindColorAlgorithm.calcForWeights + ReportResult.calcColor
# ─────────────────────────────────────────────────────────────────────────────
ORANGE = 0
GREEN  = 1
BLUE   = 2
YELLOW = 3

# BrainDNA MindColorAlgorithm.factorFirstRange 各顏色 f1=gamma/alpha 的範圍
# 注意：calcForWeights 對 f2 也用同一個 factorFirstRange 做過濾
_COLOR_F1_RANGE = {
    ORANGE: (0.25, 0.40),
    GREEN:  (0.20, 0.45),
    BLUE:   (0.30, 0.55),
    YELLOW: (0.15, 0.35),
}

# BrainDNA evaluationReport.py 常數
_PRIORITY_ORDER = 213      # 決策優先順序：次位→1(綠)，首位→2(藍)
_PRIORITY_THAN  = 0xD5F1   # 兩色決選時的優先矩陣
_COUNT_GREEN    = 2        # 綠色至少需 2 票才算數
_COUNT_BLUE     = 2        # 藍色至少需 2 票
_COUNT_YELLOW   = 2        # 黃色至少需 2 票


def _arr_mean(arr: List) -> float:
    return sum(arr) / len(arr) if arr else 0.0


def _factor_first_range(color: int, factor: float) -> bool:
    """BrainDNA MindColorAlgorithm.factorFirstRange"""
    r = _COLOR_F1_RANGE.get(color)
    if r is None:
        return False
    bottom, top = r
    return bottom < factor < top


def _calc_color_for_weights(ha: float, la: float, hb: float, lb: float,
                              lg: float, mg: float) -> int:
    """
    BrainDNA MindColorAlgorithm.calcForWeights（PRIORITY_ORDER=213）
    給定 6 個頻段平均值，回傳 MindColor（0=橙, 1=綠, 2=藍, 3=黃）。

    邏輯：
    1. f1 = gamma/alpha，f2 = gamma/beta（不乘 100，直接用比例）
    2. 第一輪：哪些顏色的 f1 在 factorFirstRange 內 → meets +1
    3. 若剛好只有 1 個顏色符合：直接回傳
    4. 第二輪：f2 不在 factorFirstRange 內的顏色 → meets -1
    5. 依 PRIORITY_ORDER 取 meets > 0 的最高優先顏色
    """
    alpha = ha + la
    beta  = hb + lb
    gamma = lg + mg
    if alpha <= 0 or beta <= 0:
        return ORANGE

    f1 = gamma / alpha   # BrainDNA 不乘 100
    f2 = gamma / beta

    meets = [0, 0, 0, 0]
    meets2 = []

    for color in range(4):
        if _factor_first_range(color, f1):
            meets[color] += 1
            meets2.append(color)

    if len(meets2) == 1:
        return meets2[0]

    # 第二輪：BrainDNA 用 factorFirstRange 檢查 f2（非 factorSecondRange）
    for color in range(4):
        if not _factor_first_range(color, f2):
            meets[color] -= 1

    # 優先順序解析：213 → 第一個從右數第二位 = 1(綠)，其次首位 = 2(藍)
    weights = _PRIORITY_ORDER
    while weights > 0:
        weights = weights // 10
        index = weights % 10
        if 0 <= index < 4 and meets[index] > 0:
            return index

    return ORANGE


def _than_to_bool(color1: int, color2: int) -> int:
    """BrainDNA _than_to_bool：兩色決選，回傳勝出顏色（PRIORITY_THAN=0xD5F1）"""
    color2_mask = 1 << color2
    i = (_PRIORITY_THAN >> (4 * color1)) & 0xF
    return color1 if (i & color2_mask) > 0 else color2


def calc_mind_color(raw_arrays: Dict[str, List]) -> int:
    """
    MindColorAlgorithm：6 視窗投票（完全對應 BrainDNA ReportResult.calcColor）

    每個視窗用 calcForWeights 算顏色，最後投票：
    - green/blue/yellow 需 ≥ 2 票才進入決選
    - 投票後 orange 票數歸零（BrainDNA：orange 只在沒有其他顏色時才勝出）
    - 只剩 1 個顏色：直接回傳
    - 只剩 2 個顏色：用 _than_to_bool 決選
    - 包含最後不足 30 秒的部分視窗（與 evaluationReport.py 第 36 行一致）
    """
    n = len(raw_arrays.get("r_lalpha") or [])

    if n < WINDOW_SIZE:
        return _calc_color_for_weights(
            _arr_mean(raw_arrays.get("r_halpha") or []),
            _arr_mean(raw_arrays.get("r_lalpha") or []),
            _arr_mean(raw_arrays.get("r_hbeta")  or []),
            _arr_mean(raw_arrays.get("r_lbeta")  or []),
            _arr_mean(raw_arrays.get("r_lgamma") or []),
            _arr_mean(raw_arrays.get("r_hgamma") or []),
        )

    # BrainDNA 最多 6 個視窗（含最後不足 30 秒的部分視窗）
    num_windows = min(math.ceil(n / WINDOW_SIZE), 6)
    mind_color_count = [0, 0, 0, 0]
    mind_color_list  = []

    for i in range(num_windows):
        start = i * WINDOW_SIZE
        end   = start + WINDOW_SIZE

        def _win_mean(key: str, _s: int = start, _e: int = end) -> float:
            arr = raw_arrays.get(key) or []
            seg = arr[_s:min(_e, len(arr))]
            return sum(seg) / len(seg) if seg else 0.0

        color = _calc_color_for_weights(
            _win_mean("r_halpha"), _win_mean("r_lalpha"),
            _win_mean("r_hbeta"),  _win_mean("r_lbeta"),
            _win_mean("r_lgamma"), _win_mean("r_hgamma"),
        )
        mind_color_count[color] += 1
        mind_color_list.append(color)

    # 套用 threshold：green/blue/yellow 需 ≥ 2 票
    count_threshold = [0, _COUNT_GREEN, _COUNT_BLUE, _COUNT_YELLOW]
    for i in range(4):
        if mind_color_count[i] < count_threshold[i]:
            mind_color_count[i] = 0

    # 若 green/blue/yellow 全為 0：回傳第一個視窗顏色（BrainDNA 預設行為）
    if mind_color_count[1] == 0 and mind_color_count[2] == 0 and mind_color_count[3] == 0:
        return mind_color_list[0] if mind_color_list else ORANGE

    # Orange 歸零（不參與最終決選）
    mind_color_count[0] = 0

    remaining = [i for i in range(4) if mind_color_count[i] > 0]

    if len(remaining) == 0:
        return ORANGE
    if len(remaining) == 1:
        return remaining[0]
    if len(remaining) == 2:
        return _than_to_bool(remaining[0], remaining[1])

    # 3+ 顏色：依 PRIORITY_ORDER 決定
    weights = _PRIORITY_ORDER
    while weights > 0:
        weights = weights // 10
        index = weights % 10
        if 0 <= index < 4 and mind_color_count[index] > 0:
            return index

    return ORANGE


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
def compute_all(raw_arrays: Dict[str, List], is_child: bool = False) -> Dict:
    """
    輸入 raw_arrays，回傳完整的 BrainDNA 指標字典。
    完全對應 BrainDNA evaluationReport.py 的資料流：

      mindColor  → report.calcColor(mindArray)     ← 全部 6 個視窗投票
      maxArray   → calcBand(mindArray)              ← best 30-second window
      bands      → helper.calcXxx(maxArray)         ← best 30s
      stress     → MindStressAlgorithm(maxArray)    ← best 30s
      balance    → MindBalanceAlgorithm(maxArray)   ← best 30s attention/medi
      energy     → MindEnergyAlgorithm(maxArray)    ← best 30s attention/medi

    自動偵測輸入尺度（raw vs norm100），確保 bandTo100 輸入也能正確運算。
    回傳字典包含 'input_scale' 欄位，標記使用的演算模式。
    """
    # ── 0. 訊號品質過濾（WebApp bandTo100 路徑補充；Android raw 路徑稍後由 delta 門檻過濾）
    raw_arrays = _filter_bad_signal_epochs(raw_arrays)

    n = len(raw_arrays.get("r_lalpha") or [])
    if n < 10:
        return {"valid": False, "input_scale": "unknown"}

    # 自動偵測輸入尺度（一次偵測，傳給所有子函式）
    scale = _detect_input_scale(raw_arrays)

    if scale == "norm100":
        # bandTo100 輸入：CAP 縮放為 100
        active_cap = {k: 100 for k in CAP}
    else:
        # best 30-second window（一次選取；兒童使用 CHILD_CAP 讓選取基準一致）
        active_cap = CHILD_CAP if is_child else CAP
    best_win = _select_best_window(
        raw_arrays, cap=active_cap,
        pr_table=CHILD_PROP_RANGE if is_child else _PROP_RANGE)

    attn = [max(0, min(100, int(v))) for v in (best_win.get("attn") or [])]
    medi = [max(0, min(100, int(v))) for v in (best_win.get("medi") or [])]

    # bands：傳入 best_win + 偵測到的 scale，讓子函式不必重複偵測
    bands = calc_band_proportions(best_win, is_child=is_child, _scale=scale)
    if bands is None:
        return {"valid": False, "input_scale": scale}

    stress  = calc_stress_score(best_win)
    balance = calc_mind_balance(attn, medi)
    energy  = calc_mind_energy(attn, medi)
    color   = calc_mind_color(raw_arrays)
    # overall_score：對應 BrainDNA evaluationReport.py 的整體分數公式
    overall = int(balance * 0.6 + energy * 0.2 + (100 - stress) * 0.2 + 0.5)

    return {
        "valid":         True,
        "input_scale":   scale,    # 'raw' 或 'norm100'，供 eeg.py 記錄 bdna_mode
        "bands":         bands,
        "stress":        stress,
        "balance":       balance,
        "energy":        energy,
        "color":         color,
        "overall_score": max(0, min(100, overall)),
    }
