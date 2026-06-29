"""
report_interpretation_engine.py
─────────────────────────────────
依照能力分數與複合指標產生 report_flags，
並為每個 flag 提供對應的中文解讀摘要。

Flag 命名規則：全小寫、底線連接（與需求文件一致）
"""
from typing import Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# Flag 定義表
# ──────────────────────────────────────────────────────────────

_FLAG_RULES = [
    # (flag_name, condition_func, interpretation_zh)
    (
        "high_focus_low_recovery",
        lambda a, c: a["focus"]["score"] >= 68 and a["relaxation"]["score"] <= 42,
        "個案呈現高專注但低放鬆的神經型態，代表其專注力可能來自高壓控制，而非穩定恢復。"
        "建議在高強度工作後安排結構化放鬆練習（呼吸調節、冥想或自然散步）。"
    ),
    (
        "high_output_low_recovery",
        lambda a, c: a["energy"]["score"] <= 40 and a["focus"]["score"] >= 65,
        "個案具備高輸出能力，但能量回補不足，容易形成高效但高耗損模式。"
        "需特別關注睡眠品質與節奏休息，避免慢性疲勞積累。"
    ),
    (
        "chronic_tension_risk",
        lambda a, c: c["sli"]["score"] >= 68 and a["relaxation"]["score"] <= 42,
        "個案可能長期處於交感神經活化狀態，需優先建立放鬆與恢復節奏。"
        "建議定期評估睡眠、壓力事件與情緒調節策略。"
    ),
    (
        "rational_dominant",
        lambda a, c: c["reb"].get("reb_flag") == "rational_dominant" and a["logic"]["score"] >= 60,
        "個案理性處理速度快，邏輯分析能力強，但情緒整合相對偏低。"
        "在人際互動或重要決策時，可能容易被他人認為過於冷靜或缺乏情感連結。"
    ),
    (
        "emotional_dominant",
        lambda a, c: c["reb"].get("reb_flag") == "emotional_dominant",
        "個案情緒感知敏銳，對他人情緒狀態反應迅速，但在高壓情境下可能難以保持理性距離。"
        "建議透過結構化思考練習提升情緒調節能力。"
    ),
    (
        "rational_dominant_emotional_delay",
        lambda a, c: a["empathy"]["score"] <= 40 and a["logic"]["score"] >= 65,
        "個案理性處理速度快，但情緒與語言同步較慢，容易被誤解為冷淡或過於直接。"
        "在關係中可主動增加情感表達的頻率，以彌補這個自然的認知落差。"
    ),
    (
        "high_intuition_low_logic",
        lambda a, c: a["intuition"]["score"] >= 68 and a["logic"]["score"] <= 40,
        "個案直覺力強，對模式辨識敏銳，但系統性邏輯分析較弱。"
        "建議在重要決策前增加結構化分析步驟，以強化直覺判斷的可靠度。"
    ),
    (
        "energy_deficit",
        lambda a, c: a["energy"]["score"] <= 38,
        "個案能量儲備偏低，可能反映長期睡眠不足、慢性壓力或恢復機制不佳。"
        "需優先改善基礎生活節奏（睡眠、飲食、適度運動）。"
    ),
    (
        "low_awareness",
        lambda a, c: a["awareness"]["score"] <= 35,
        "個案對外部環境的即時感知與整合能力偏低，可能在多工環境或社交場合中較難保持注意力廣度。"
    ),
    (
        "high_emotional_delay",
        lambda a, c: c["edc"]["score"] >= 68,
        "個案情緒處理延遲明顯，可能在事後才意識到自己的情緒反應。"
        "建議練習情緒即時覺察（身體感知、情緒日誌），縮短情緒感知與表達之間的落差。"
    ),
    (
        "low_interpersonal_sync",
        lambda a, c: c["isi"]["score"] <= 35,
        "個案人際情緒同步能力偏低，在團隊合作或親密關係中可能出現節奏落差。"
        "建議增加面對面互動與主動傾聽練習。"
    ),
    (
        "theta_dominant",
        lambda a, c: a["intuition"]["score"] >= 72,
        "個案 theta 波活躍，與高直覺力、潛意識整合及創意思維相關。"
        "適合從事需要洞察力的工作，但在需要快速決策的高壓環境中要注意能量分配。"
    ),
    (
        "high_stress_burnout_pattern",
        lambda a, c: c["sli"]["score"] >= 70 and c["ebi"]["score"] <= 35,
        "個案同時呈現高壓力負荷與低能量回補，是典型的「燃盡（burnout）風險」型態。"
        "建議立即評估工作負荷，並建立強制性恢復節奏（每週至少一個完整休息日）。"
    ),
]


# ──────────────────────────────────────────────────────────────
# 主函數
# ──────────────────────────────────────────────────────────────

def generate_report_flags(
    ability_scores: Dict[str, dict],
    composite_indices: Dict[str, dict],
    signal_quality: dict,
) -> List[dict]:
    """
    根據能力分數與複合指標觸發 report_flags。

    Returns:
        List of {
          "flag": str,
          "interpretation": str,
          "priority": "high" | "medium" | "low"
        }
    """
    flags = []

    if signal_quality.get("quality_grade") == "D":
        flags.append({
            "flag": "signal_quality_insufficient",
            "interpretation": "訊號品質不足（D 級），分析結果僅供參考，建議重新檢測。",
            "priority": "high"
        })
        return flags

    high_priority = {
        "chronic_tension_risk", "high_stress_burnout_pattern",
        "high_output_low_recovery", "energy_deficit"
    }
    medium_priority = {
        "high_focus_low_recovery", "rational_dominant_emotional_delay",
        "high_emotional_delay", "low_interpersonal_sync", "emotional_dominant"
    }

    for flag_name, condition, interpretation in _FLAG_RULES:
        try:
            if condition(ability_scores, composite_indices):
                priority = ("high" if flag_name in high_priority
                            else "medium" if flag_name in medium_priority
                            else "low")
                flags.append({
                    "flag": flag_name,
                    "interpretation": interpretation,
                    "priority": priority,
                })
        except Exception:
            pass

    # 依優先順序排列
    priority_order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda x: priority_order.get(x["priority"], 3))
    return flags


def generate_report_summary(
    ability_scores: Dict[str, dict],
    composite_indices: Dict[str, dict],
    flags: List[dict],
    subject_name: str = "",
    age: Optional[int] = None,
) -> str:
    """
    生成報告摘要文字（供報告首頁使用）
    """
    top_abilities = sorted(ability_scores.items(), key=lambda x: -x[1]["score"])[:3]
    low_areas = [k for k, v in ability_scores.items() if v["score"] <= 38]

    name_str = f"{subject_name}的" if subject_name else "受測者的"
    lines = [f"【腦波分析摘要】"]

    # 優勢
    ability_map = {
        "intuition": "直覺洞察力", "energy": "能量續航",
        "relaxation": "內在安定", "focus": "高度專注",
        "logic": "邏輯分析", "awareness": "外界覺察", "empathy": "共情柔軟"
    }
    top_names = "、".join(ability_map.get(k, k) for k, _ in top_abilities)
    lines.append(f"{name_str}腦波顯示主要優勢為：{top_names}。")

    if low_areas:
        low_names = "、".join(ability_map.get(k, k) for k in low_areas)
        lines.append(f"相對需要關注的面向：{low_names}。")

    high_flags = [f for f in flags if f["priority"] == "high"]
    if high_flags:
        lines.append(f"重要提示：{high_flags[0]['interpretation']}")

    lines.append(
        "\n本報告所呈現之腦波數值，係依據受測者原始腦波資料，"
        "經 log power 轉換、內部常模 Z-score 標準化與 0–100 分數轉換後所得。"
        "此結果主要用於心理發展、壓力調節、職能分析與自我覺察參考，"
        "非臨床診斷、醫療判定或疾病分類依據。"
        "本次分析使用 ThinkGear 單導程（Fp1）內部常模資料庫進行標準化。"
    )

    return "\n".join(lines)
