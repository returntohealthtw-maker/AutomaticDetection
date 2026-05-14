"""
腦波報告整合模組（從 BrainDNA evaluationReport.py 移植）

提供兩個高階 API：

  1) generate_report(esense_rows)
     接收 N 筆腦波時序資料（每筆 dict 含 attention/meditation/8 個頻段），
     回傳完整報告 dict：4 色腦人 + 8 卦 + MBTI + 三大分數 + 文案 + 評語。

  2) generate_quick_mbti(eeg_means)
     簡版：直接給 8 個頻段平均值，回傳 MBTI + 4 色腦人 + 八卦。
     用於「腦波量測完成後立即顯示 MBTI」的快速結果。

esense_rows 格式範例：
    [
        {
            "ts": 0.5,
            "attention": 65, "meditation": 50,
            "delta": 12345, "theta": 8765,
            "lowAlpha": 4321, "highAlpha": 5432,
            "lowBeta": 3210, "highBeta": 4567,
            "lowGamma": 1234, "midGamma": 2345
        },
        ...
    ]
"""
from typing import List, Dict, Any
import math

from app.algorithms.brainwave import (
    MindBalanceAlgorithm,
    MindEnergyAlgorithm,
    MindStressAlgorithm,
    MindColorAlgorithm,
    MindValueAlgorithm,
    MindValueCalcHelper,
    ReportResult,
)
from app.algorithms.bagua import Bagua
from app.algorithms.mbti import Personality
from app.algorithms.data_stats import DATA_STATS, DATA_VALUES


# ─── 繁中文案（從 evaluationReport.py 抽出）────────────────────────────────

QUADRANT_THRESHOLD = 50
PRIORITY_ORDER     = 213
PRIORITY_THAN      = 0xD5F1
COUNT_YELLOW       = 2
COUNT_BLUE         = 2
COUNT_GREEN        = 2

MIND_COLOR_STRINGS = ["橘腦人", "綠腦人", "藍腦人", "黃腦人"]
MIND_COLOR_STRINGS_EN = ["Orange Brainer", "Green Brainer", "Blue Brainer", "Yellow Brainer"]
MIND_COLOR_CHARACTERISTICS = [
    "活蹦亂跳的開心果",
    "努力工作的建築師",
    "才華洋溢的夢想家",
    "權威的守護者",
]
MIND_COLOR_CHARACTERISTIC_DESC = [
    "橘腦人對周遭環境總是充滿正面樂觀的希望，事事衝第一，想到什麼就做什麼，永遠有用不完的活力與能量，他們最崇尚就是冒險與自由！\n"
    "橘腦人擁有熱情及開朗的俠義精神，是一位充滿自信的唐吉珂德追隨者。\n"
    "適合職業：護理師、運動員、消防員",

    "綠腦的人具備沈著內斂的人格特質，他們總是可以運用理性分析完成交付的任務，不要看他在旁邊默不作聲，其實心裡已經有一整套獨到的想法！\n"
    "綠腦的人特別具備排除一切困難的超強執行力，特別擅長解決需要精準解決的複雜問題，是眾人中最冷靜且實作型的人才。\n"
    "適合職業：工程師、律師、會計師",

    "藍腦的人兼具智慧與慈愛的特質，特別富有創造力，思考總是天馬行空漫無邊際！\n"
    "藍腦的人十分重視關係的和平與同時十分感性且樂於分享。他們用獨到的敏銳觀察力來觀察生活，是一位與生俱來的生活藝術哲學家。\n"
    "適合職業：藝術家、設計師、兒童照顧專家",

    "黃腦的人擁有過人的腦力與執行力，做事情講求是非分明，善用邏輯思考行事，是企劃和執行的專家！\n"
    "黃腦的人做事負責，能按部就班的指派並完成任務，大事只要交給他來掌舵就沒錯了！是天生領導特質的人才喔！\n"
    "適合職業：執行長、企業家、教育家",
]

BAND_DESCRIPTIONS = [
    {"name": "Delta 深度休息", "desc": "Delta 波代表深度休息與睡眠品質的指標。"},
    {"name": "Theta 直覺能力", "desc": "Theta 波 70 分以上代表直覺能力正常；85 以上具有極佳的直覺能力，是優秀企業家與領導者必備的能力。"},
    {"name": "High Alpha 氣血飽滿", "desc": "High Alpha 60 分以上為正常範圍；80 以上代表氣血相當飽滿、精神充沛。創業需要足夠的體力以及精神去面對一切的困難。"},
    {"name": "Low Alpha 內在安定", "desc": "Low Alpha 70 分以上有超強的定力；85 以上是大師級的定力。創業會碰到許多事情以及內在與外在的壓力，內在安定可以讓你在有壓力下處變不驚想出解決方案。"},
    {"name": "High Beta 高度專注", "desc": "High Beta 表示在任何地方都可以瞬間對外在環境做出專注的觀察與正確的反應。70 分以上代表有極佳的動專注力。"},
    {"name": "Low Beta 邏輯分析", "desc": "Low Beta 表示在專心做一件事情、寫企劃案或做功課時能保持高度專注，進行深度的思考。60 分以上代表擁有好的邏輯思維。"},
    {"name": "Mid Gamma 觀察環境", "desc": "Mid Gamma 表示大腦的天線非常發達，能對周圍事情、氣場變化及談判中大家的心情變化做出細微的觀察。75 以上具有高度敏銳。"},
    {"name": "Low Gamma 慈悲柔軟", "desc": "Low Gamma 是慈悲的指數。越慈悲的人大家越喜歡靠近你，70 以上是高、80 以上極高，內心柔軟、很為人著想。"},
]

MIND_COLOR_POSTS = [
    "感動投資人的財務長 CFO",
    "使命必達的營運長 COO",
    "創意無限的技術長 CTO",
    "運籌帷幄的執行長 CEO",
]

MIND_COLOR_POST_DESCRIPTIONS = [
    "橘腦人對周遭環境總是充滿正面樂觀的希望，永遠有用不完的活力與能量。\n"
    "橘腦人擁有熱情和開朗的精神，是團隊中的催化劑。\n"
    "他們有路見不平拔刀相助的精神，熱情往往能感染團隊、帶動團隊。\n"
    "橘腦人在組織裡面適合做許多工作，尤其是財務長，因為他們能感動投資人。",

    "綠腦人總是可以運用理性分析完成交付任務，常常他在旁邊悶不作聲，其實心裡已經有一套獨到的想法。\n"
    "綠腦人具有超強的執行力，特別擅長解決複雜的問題。做事嚴謹、任勞任怨的個性常能贏得團隊的尊重。\n"
    "在新創團隊裡面是最難得可貴的人才。",

    "藍腦人特別富有想像力，他們用獨到的敏感觀察力來觀察生活，能幫助團隊在遇到困境的時候想出很棒的創意和想法。\n"
    "他們特殊的直覺與洞察力，可以在眾多技術平台中間選出公司最需要的技術，是公司發展過程中能想出獨角獸產品的奇葩。",

    "黃腦人擁有過人的腦力與執行力，做事情講求是非分明，善於邏輯思考行事，能夠按部就班地指派並完成任務。\n"
    "最適合當公司的執行長：黃腦人不會異想天開、不會光說不練，只要決定了就會去做，是創業初期團隊的領導人物。",
]


# ─── 三大分數的評語 ────────────────────────────────────────────────────────

def _balance_comment(score: int) -> str:
    if score > 80: return "目前為最佳狀態，擁有巔峰極致的潛力"
    if score > 60: return "身心平衡狀態不錯，多讓自己保持平靜的狀態"
    if score > 40: return "身心平衡狀態尚可，可以試著進行身心同步練習"
    return "身心狀態呈現失衡，可試著調整好作息與睡眠品質"


def _energy_comment(score: int) -> str:
    if score > 80: return "腦力程度極佳，擁有高超的腦力以及執行力"
    if score > 60: return "腦力程度佳，具有邏輯表達與思考能力"
    if score > 40: return "腦力程度適中，還需多加強靜心能力方可維持良好的腦力"
    return "腦力呈現疲勞狀態，建議好好休息保持良好的放鬆"


def _stress_comment(score: int) -> str:
    if score > 80: return "壓力達到緊繃狀態，需注重身心健康的警訊"
    if score > 60: return "壓力指數高，試著保持放鬆平穩的情緒"
    if score > 40: return "壓力指數尚可，目前需注意身心平衡狀態"
    return "壓力指數低，目前身心壓力指數為正常"


def _therapy_suggestion(score: int) -> str:
    if score > 80: return "利用個人腦波音樂療程提升自我療癒能力"
    if score > 60: return "每天使用腦波音樂療程，並搭配使用放鬆音樂"
    if score > 40: return "使用個人腦波音樂服務，促進身心更加平衡與健康"
    return "先進行客製化腦波音樂評測，每天持續使用療程音樂"


def _score_comment(score: int) -> str:
    if score > 80: return "大腦與身心健康狀態表現極佳"
    if score > 60: return "身心健康狀態良好，請記得保持愉快身心"
    if score > 40: return "目前程度適中，需要更充足的休息"
    return "待加強！身心健康狀態需要好好注意"


# ─── 高階 API ────────────────────────────────────────────────────────────

def generate_quick_mbti(eeg_means: Dict[str, float]) -> Dict[str, Any]:
    """
    快速 MBTI 推算（給已平均過的 8 頻段值）

    Args:
        eeg_means: dict，需含 highAlpha, lowAlpha, highBeta, lowBeta,
                   lowGamma, midGamma, theta（key 名稱與 NeuroSky 一致）

    Returns:
        dict { mind_color, mind_color_name, bagua, bagua_name, mbti, mbti_zh }
    """
    ha = float(eeg_means.get("highAlpha", 0))
    la = float(eeg_means.get("lowAlpha",  0))
    hb = float(eeg_means.get("highBeta",  0))
    lb = float(eeg_means.get("lowBeta",   0))
    lg = float(eeg_means.get("lowGamma",  0))
    mg = float(eeg_means.get("midGamma",  0))
    th = float(eeg_means.get("theta",     0))

    color = MindColorAlgorithm.calc(ha, la, hb, lb, lg, mg)
    bagua = Bagua.calcBagua(color, la)
    mbti  = Personality.getPersonalityFromBagua(bagua, th)

    return {
        "mind_color":      color,
        "mind_color_name": MIND_COLOR_STRINGS[color],
        "bagua":           bagua.id,
        "bagua_name":      bagua.name,
        "mbti":            mbti.id,
        "mbti_zh":         mbti.name_zh,
        "mbti_en":         mbti.name,
    }


def generate_report(esense_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    完整報告生成器

    Args:
        esense_rows: 時序腦波 list，每筆需含 attention, meditation,
                     delta, theta, lowAlpha, highAlpha, lowBeta, highBeta,
                     lowGamma, midGamma（NeuroSky ThinkGear 標準欄位）

    Returns:
        report dict
    """
    if not esense_rows:
        raise ValueError("esense_rows 不可為空")

    # 切成 30 秒一段
    mind_array = []
    tmp = []
    for row in esense_rows:
        tmp.append(row)
        if len(tmp) >= 30:
            mind_array.append(tmp)
            tmp = []
    if tmp:
        mind_array.append(tmp)

    # ─── 4 色腦人 ───
    report = ReportResult()
    mind_color = report.calcColor(
        mind_array, PRIORITY_ORDER, PRIORITY_THAN,
        COUNT_YELLOW, COUNT_BLUE, COUNT_GREEN,
    )
    mind_color_list = report.mindColorList

    # ─── 取最強的 30 秒段做後續分析 ───
    max_idx = MindValueAlgorithm.calcBand(mind_array)
    max_section = mind_array[max_idx]

    attention   = MindValueAlgorithm.getArray(max_section, "attention")
    meditation  = MindValueAlgorithm.getArray(max_section, "meditation")
    delta       = MindValueAlgorithm.getArray(max_section, "delta")
    theta       = MindValueAlgorithm.getArray(max_section, "theta")
    low_alpha   = MindValueAlgorithm.getArray(max_section, "lowAlpha")
    high_alpha  = MindValueAlgorithm.getArray(max_section, "highAlpha")
    low_beta    = MindValueAlgorithm.getArray(max_section, "lowBeta")
    high_beta   = MindValueAlgorithm.getArray(max_section, "highBeta")
    low_gamma   = MindValueAlgorithm.getArray(max_section, "lowGamma")
    mid_gamma   = MindValueAlgorithm.getArray(max_section, "midGamma")

    # ─── 三大分數 ───
    mind_balance = MindBalanceAlgorithm.calc(attention, meditation)
    mind_energy  = MindEnergyAlgorithm.calc(attention, meditation)
    mind_stress  = MindStressAlgorithm.calc(mid_gamma, low_alpha)

    # ─── 各頻段 strip 值（0~100 比例）───
    helper = MindValueCalcHelper(MindValueCalcHelper.Algorithm["proportion"])
    helper.calcColumnSumArray(delta, high_alpha, low_alpha, high_beta, low_beta, low_gamma, mid_gamma, theta)
    helper.calcDelta(delta)
    helper.calcHighAlpha(high_alpha)
    helper.calcLowAlpha(low_alpha)
    helper.calcHighBeta(high_beta)
    helper.calcLowBeta(low_beta)
    helper.calcLowGamma(low_gamma)
    helper.calcMidGamma(mid_gamma)
    helper.calcTheta(theta)

    bands = [
        {"name": BAND_DESCRIPTIONS[0]["name"], "value": int(helper.delta     * 100 + 0.5), "desc": BAND_DESCRIPTIONS[0]["desc"]},
        {"name": BAND_DESCRIPTIONS[1]["name"], "value": int(helper.theta     * 100 + 0.5), "desc": BAND_DESCRIPTIONS[1]["desc"]},
        {"name": BAND_DESCRIPTIONS[2]["name"], "value": int(helper.highAlpha * 100 + 0.5), "desc": BAND_DESCRIPTIONS[2]["desc"]},
        {"name": BAND_DESCRIPTIONS[3]["name"], "value": int(helper.lowAlpha  * 100 + 0.5), "desc": BAND_DESCRIPTIONS[3]["desc"]},
        {"name": BAND_DESCRIPTIONS[4]["name"], "value": int(helper.highBeta  * 100 + 0.5), "desc": BAND_DESCRIPTIONS[4]["desc"]},
        {"name": BAND_DESCRIPTIONS[5]["name"], "value": int(helper.lowBeta   * 100 + 0.5), "desc": BAND_DESCRIPTIONS[5]["desc"]},
        {"name": BAND_DESCRIPTIONS[6]["name"], "value": int(helper.midGamma  * 100 + 0.5), "desc": BAND_DESCRIPTIONS[6]["desc"]},
        {"name": BAND_DESCRIPTIONS[7]["name"], "value": int(helper.lowGamma  * 100 + 0.5), "desc": BAND_DESCRIPTIONS[7]["desc"]},
    ]

    overall = int(mind_balance * 0.6 + mind_energy * 0.2 + (100 - mind_stress) * 0.2 + 0.5)

    # ─── 八卦 + MBTI ───
    sorted_colors = MindColorAlgorithm.sortColor(mind_color_list)
    bagua = Bagua.calcBaguaFromColors(sorted_colors)

    avg_low_beta  = MindValueAlgorithm.average(MindValueAlgorithm.getArray(esense_rows, "lowBeta"))
    avg_high_beta = MindValueAlgorithm.average(MindValueAlgorithm.getArray(esense_rows, "highBeta"))
    avg_theta     = MindValueAlgorithm.average(MindValueAlgorithm.getArray(esense_rows, "theta"))
    beta_mean     = (avg_low_beta + avg_high_beta) / 2

    mbti = Personality.calcPersonality(bagua, sorted_colors, avg_theta, beta_mean)

    # ─── attention / meditation pie ───
    att_pie = MindValueAlgorithm.calcMindPie(attention)
    med_pie = MindValueAlgorithm.calcMindPie(meditation)
    att_total = (att_pie[0] + att_pie[1] + att_pie[2]) or 1
    med_total = (med_pie[0] + med_pie[1] + med_pie[2]) or 1
    att_percentage = int((att_pie[1] + att_pie[2]) / att_total * 100)
    med_percentage = int((med_pie[1] + med_pie[2]) / med_total * 100)

    # ─── quadrant 象限 ───
    att_avg = MindValueAlgorithm.average(attention)
    med_avg = MindValueAlgorithm.average(meditation)
    if att_avg > QUADRANT_THRESHOLD:
        quadrant = 0 if med_avg > QUADRANT_THRESHOLD else 3
    else:
        quadrant = 1 if med_avg > QUADRANT_THRESHOLD else 2

    return {
        # ─── 概覽 ───
        "overall_score":   overall,
        "score_comment":   _score_comment(overall),
        "therapy_suggestion": _therapy_suggestion(overall),

        # ─── 三大分數 ───
        "mind_balance":         mind_balance,
        "mind_balance_comment": _balance_comment(mind_balance),
        "mind_energy":          mind_energy,
        "mind_energy_comment":  _energy_comment(mind_energy),
        "mind_stress":          mind_stress,
        "mind_stress_comment":  _stress_comment(mind_stress),

        # ─── 4 色腦人 ───
        "mind_color":            mind_color,
        "mind_color_name":       MIND_COLOR_STRINGS[mind_color],
        "mind_color_name_en":    MIND_COLOR_STRINGS_EN[mind_color],
        "mind_color_character":  MIND_COLOR_CHARACTERISTICS[mind_color],
        "mind_color_character_desc": MIND_COLOR_CHARACTERISTIC_DESC[mind_color],
        "mind_color_post":       MIND_COLOR_POSTS[mind_color],
        "mind_color_post_desc":  MIND_COLOR_POST_DESCRIPTIONS[mind_color],
        "mind_color_list":       mind_color_list,
        "mind_color_results":    [MIND_COLOR_STRINGS[c] for c in mind_color_list],

        # ─── 八卦 + MBTI ───
        "bagua":      bagua.id,
        "bagua_name": bagua.name,
        "mbti":       mbti.id,
        "mbti_zh":    mbti.name_zh,
        "mbti_en":    mbti.name,

        # ─── 8 個頻段 ───
        "bands": bands,

        # ─── attention / meditation ───
        "attention_proportions":  att_pie,
        "meditation_proportions": med_pie,
        "attention_percentage":   att_percentage,
        "meditation_percentage":  med_percentage,
        "quadrant":               quadrant,
    }
