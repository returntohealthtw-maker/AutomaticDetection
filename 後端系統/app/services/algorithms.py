"""
腦波演算法計算引擎
依據設計文件 01_演算法整理與修正.md 及 07_SDK資料需求與後端演算法.md
"""
from dataclasses import dataclass
from typing import List, Optional
import math


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


def compute_mbti(avg: BandAverages) -> dict:
    """
    計算 MBTI 傾向（僅 EEG 部分，70% 權重）
    回傳各維度分數（0~100，>50 傾向第一字母）
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

    # E/I：β/α 比值（Mindsensor 為 Fp1 單通道，無法計算 FAA）
    # β/α > 1 → 外向(E)；β/α < 1 → 內向(I)
    alpha_avg = (ha + la) if (ha + la) > 0 else 1
    beta_avg  = (hb + lb) if (hb + lb) > 0 else 1
    ei_raw = _safe_div(beta_avg, alpha_avg)           # β/α 比值
    ei_pct = _clamp(1 / (1 + math.exp(-3 * (ei_raw - 1))) * 100, 0, 100)  # >50 = E

    # N/S：Theta / Beta（高 Theta = 直覺 N；高 Beta = 感官 S）
    ns_raw = _safe_div(t, b)
    ns_pct = _clamp(1 / (1 + math.exp(-3 * (ns_raw - 1))) * 100, 0, 100)  # >50 = N

    # T/F：Low Beta / (Low Gamma + Theta)（高邏輯 = T；高情感 = F）
    tf_raw = _safe_div(lb, lg + t)
    tf_pct = _clamp(1 / (1 + math.exp(-3 * (tf_raw - 1))) * 100, 0, 100)  # >50 = T

    # J/P：High Beta / Theta（高執行 = J；高直覺彈性 = P）
    jp_raw = _safe_div(hb, t)
    jp_pct = _clamp(1 / (1 + math.exp(-3 * (jp_raw - 1))) * 100, 0, 100)  # >50 = J

    mbti_type = (
        ("E" if ei_pct >= 50 else "I") +
        ("N" if ns_pct >= 50 else "S") +
        ("T" if tf_pct >= 50 else "F") +
        ("J" if jp_pct >= 50 else "P")
    )

    return {
        "mbti_type":  mbti_type,
        "ei_score":   round(ei_pct, 1),
        "ns_score":   round(ns_pct, 1),
        "tf_score":   round(tf_pct, 1),
        "jp_score":   round(jp_pct, 1),
        "ei_label":   "E" if ei_pct >= 50 else "I",
        "ns_label":   "N" if ns_pct >= 50 else "S",
        "tf_label":   "T" if tf_pct >= 50 else "F",
        "jp_label":   "J" if jp_pct >= 50 else "P",
        "confidence": round(
            (abs(ei_pct-50) + abs(ns_pct-50) + abs(tf_pct-50) + abs(jp_pct-50)) / 2, 1
        )
    }
