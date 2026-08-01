"""
報告章節結構定義

Phase 1：先用固定佔位章節（移植自 HomeAnalysisReport 的成熟結構）
Phase 2：改為從 GitHub 私有 repo 動態讀取（BrianaveReportImage 等）

╔══════════════════════════════════════════════════════════════════╗
║ 4 種報告類型 × 多種版本                                            ║
╠══════════════════════════════════════════════════════════════════╣
║ 腦波分析人生劇本（成人）                                            ║
║   ├ 體驗版：只顯示 第 1、3、8、12 章                                ║
║   ├ 完整版：全部 12 章                                              ║
║   └ VIP 版：全部 12 章                                              ║
║                                                                    ║
║ 兒童腦波天賦解碼                                                    ║
║   ├ 體驗版：只顯示 第 1、3、8、12 章                                ║
║   ├ 完整版：全部 12 章                                              ║
║   └ VIP 版：全部 12 章                                              ║
║                                                                    ║
║ 親子腦波共振關係報告（已有 = HomeAnalysisReport）                   ║
║ 夫妻腦波共振關係報告（marital-report）                              ║
╚══════════════════════════════════════════════════════════════════╝
"""
from typing import List, Dict


# ─── 腦波分析人生劇本（成人）──────────────────────────────────────────────
# Phase 1 暫定章節結構（後續會被 BrianaveReportImage repo 內容取代）
LIFE_SCRIPT_CHAPTERS: List[Dict] = [
    {
        "num": 1, "icon": "🌱",
        "title": "你的腦波 DNA：人生劇本的科學總覽",
        "sections": [
            {"num": 1, "title": "腦波七大指標的個人化解析"},
            {"num": 2, "title": "你的心智顏色：4 色腦人類型"},
            {"num": 3, "title": "MBTI 性格定位與優勢"},
            {"num": 4, "title": "為什麼你會是現在的你"},
        ],
    },
    {
        "num": 2, "icon": "👶",
        "title": "童年烙印：原生家庭如何雕塑你的大腦",
        "sections": [
            {"num": 1, "title": "0-6 歲：神經迴路的奠基期"},
            {"num": 2, "title": "童年情緒記憶在腦波的痕跡"},
            {"num": 3, "title": "依附類型對成人關係的影響"},
            {"num": 4, "title": "重新養育自己的腦科學方法"},
        ],
    },
    {
        "num": 3, "icon": "💼",
        "title": "天賦解碼：你最適合的職涯方向",
        "sections": [
            {"num": 1, "title": "你的核心優勢與隱藏才華"},
            {"num": 2, "title": "適合的工作型態與環境"},
            {"num": 3, "title": "團隊中的最佳角色定位"},
            {"num": 4, "title": "領導 vs 執行：你的天然位置"},
        ],
    },
    {
        "num": 4, "icon": "💔",
        "title": "感情劇本：你在親密關係中的腦波模式",
        "sections": [
            {"num": 1, "title": "你愛人與被愛的方式"},
            {"num": 2, "title": "衝突時的神經反應模式"},
            {"num": 3, "title": "什麼樣的伴侶能與你共振"},
            {"num": 4, "title": "感情升溫的具體腦科學策略"},
        ],
    },
    {
        "num": 5, "icon": "💰",
        "title": "金錢腦波學：你與財富的關係",
        "sections": [
            {"num": 1, "title": "你對金錢的潛意識信念"},
            {"num": 2, "title": "投資/儲蓄/消費的神經傾向"},
            {"num": 3, "title": "豐盛思維 vs 匱乏思維的腦波差異"},
            {"num": 4, "title": "重塑財富腦的具體練習"},
        ],
    },
    {
        "num": 6, "icon": "⚡",
        "title": "壓力與情緒：你的神經系統運作模式",
        "sections": [
            {"num": 1, "title": "你的壓力反應類型（戰/逃/凍結）"},
            {"num": 2, "title": "情緒爆發的早期訊號"},
            {"num": 3, "title": "屬於你的快速冷靜技術"},
            {"num": 4, "title": "建立情緒韌性的腦波訓練"},
        ],
    },
    {
        "num": 7, "icon": "🌙",
        "title": "睡眠與能量：你的修復系統",
        "sections": [
            {"num": 1, "title": "你的最佳作息類型（晨型/夜型）"},
            {"num": 2, "title": "Delta/Theta 揭示的深層疲憊"},
            {"num": 3, "title": "白天能量管理的個人化方案"},
            {"num": 4, "title": "深度修復的睡前儀式"},
        ],
    },
    {
        "num": 8, "icon": "🎯",
        "title": "潛意識深處：你內在的真實渴望",
        "sections": [
            {"num": 1, "title": "Theta 波揭示的潛意識訊息"},
            {"num": 2, "title": "未被滿足的核心需求"},
            {"num": 3, "title": "童年夢想 vs 現實人生"},
            {"num": 4, "title": "與潛意識對話的具體方法"},
        ],
    },
    {
        "num": 9, "icon": "🌟",
        "title": "靈感與創造力：你的天才開關",
        "sections": [
            {"num": 1, "title": "Alpha/Gamma 揭示的創意潛能"},
            {"num": 2, "title": "進入心流（Flow）狀態的條件"},
            {"num": 3, "title": "突破創意瓶頸的腦波技術"},
            {"num": 4, "title": "讓靈感成為日常的環境設計"},
        ],
    },
    {
        "num": 10, "icon": "🧭",
        "title": "人生方向：你的使命感地圖",
        "sections": [
            {"num": 1, "title": "腦波揭示的人生主題"},
            {"num": 2, "title": "你在這個時代的獨特位置"},
            {"num": 3, "title": "「該做」vs「想做」的內在拉扯"},
            {"num": 4, "title": "找到你的「為什麼」"},
        ],
    },
    {
        "num": 11, "icon": "🛡️",
        "title": "風險防範：你最容易陷入的心理陷阱",
        "sections": [
            {"num": 1, "title": "你的盲點與重複劇本"},
            {"num": 2, "title": "壓力下最容易退化的模式"},
            {"num": 3, "title": "警訊出現時的辨識指南"},
            {"num": 4, "title": "立即可用的自救工具"},
        ],
    },
    {
        "num": 12, "icon": "📅",
        "title": "六個月人生升級計畫：每週可執行藍圖",
        "sections": [
            {"num": 1, "title": "第 1-6 週：覺察與穩定期"},
            {"num": 2, "title": "第 7-12 週：解構與整合期"},
            {"num": 3, "title": "第 13-18 週：重塑與練習期"},
            {"num": 4, "title": "第 19-24 週：固化新人生期"},
        ],
    },
]

# 體驗版只顯示這些章節
TRIAL_CHAPTERS = {1, 3, 8, 12}


# ─── 青少年未來人生戰略發展（13-17 歲）──────────────────────────────────────
# 內容與 teen-report-app（沿用「國際心教育」青少年學生版）的
# CHAPTER_DEFS_XIN_TEEN_STUDENT 完全一致，僅供後台監看頁顯示章節標題/計數用，
# 實際內容生成邏輯在 teen-report-app 的 geminiService.ts。
TEEN_CHAPTERS: List[Dict] = [
    {"num": 1, "icon": "🚀", "title": "啟動超能力：認識我的五維升級模型", "sections": [
        {"num": 1, "title": "我的五大升學優勢（最強的競爭武器）"},
        {"num": 2, "title": "五大武器整合圖譜"},
        {"num": 3, "title": "從各種檢測項目找出我的隱藏潛力"},
        {"num": 4, "title": "準備繪製專屬我的升學與未來發展戰略圖"},
    ]},
    {"num": 2, "icon": "🎭", "title": "破解性格密碼：考試壓力下的真實自我", "sections": [
        {"num": 1, "title": "能量模式：壓力下我會社交還是獨處？"},
        {"num": 2, "title": "學習風格：我偏細節還是整體？"},
        {"num": 3, "title": "決策大腦：我偏邏輯還是偏感受？"},
        {"num": 4, "title": "時間管理：我規劃派還是彈性派？"},
    ]},
    {"num": 3, "icon": "🧠", "title": "挖掘大腦潛能：我的學科優勢在哪裡？", "sections": [
        {"num": 1, "title": "我的抽象邏輯與複雜閱讀能力體檢"},
        {"num": 2, "title": "我是系統整合高手還是創新發想達人？"},
        {"num": 3, "title": "站上舞台：表達力與研究專注力"},
        {"num": 4, "title": "找出我的學科競爭優勢象限"},
    ]},
    {"num": 4, "icon": "💪", "title": "鍛鍊鋼鐵心智：成長型思維與抗壓力", "sections": [
        {"num": 1, "title": "改變大腦：我相信能力是可以改變的嗎？"},
        {"num": 2, "title": "失敗復原術：我的失敗反應模式"},
        {"num": 3, "title": "撕下標籤：努力是投資不是評價"},
        {"num": 4, "title": "壓力測試：面對排名的心理彈性與專注維持"},
    ]},
    {"num": 5, "icon": "🤝", "title": "人際生存法則：情緒與社群壓力應對", "sections": [
        {"num": 1, "title": "自我覺察：我是否過度依賴外界評價？"},
        {"num": 2, "title": "情緒急救：穩定情緒與快速恢復"},
        {"num": 3, "title": "抗群壓力：我會跟風還是獨立？"},
        {"num": 4, "title": "負責任決策：學會延遲滿足並考慮長期後果"},
    ]},
    {"num": 6, "icon": "🛠️", "title": "成為學習駭客：最關鍵的自主學習力", "sections": [
        {"num": 1, "title": "抓 Bug 能力：我看得出自己的弱點嗎？"},
        {"num": 2, "title": "目標拆解術：我能順利制定複習計畫嗎？"},
        {"num": 3, "title": "動態微調：我會修正讀書策略並優化流程嗎？"},
        {"num": 4, "title": "覆盤進化論：成敗反思與長期優化"},
    ]},
    {"num": 7, "icon": "📡", "title": "看懂我的戰力雷達圖：五大維度總體檢", "sections": [
        {"num": 1, "title": "解密我的升學人格適配圖與學科優勢"},
        {"num": 2, "title": "檢視我的抗壓韌性與情緒社交穩定度"},
        {"num": 3, "title": "我的自主學習成熟度到哪一個等級？"},
        {"num": 4, "title": "我是獨立作戰派，還是需要高監督型環境？"},
    ]},
    {"num": 8, "icon": "🗺️", "title": "畫出升學地圖：找出最配我的科系與環境", "sections": [
        {"num": 1, "title": "打造屬於我的最佳學習環境"},
        {"num": 2, "title": "應試派還是研究派？我的最佳策略"},
        {"num": 3, "title": "科系大哉問：理工／商管／人文社科"},
        {"num": 4, "title": "國際競賽適配度與我的升學優勢路徑"},
    ]},
    {"num": 9, "icon": "🎯", "title": "實戰演練：破解焦慮與群體效應", "sections": [
        {"num": 1, "title": "擺脫比較心態：群體比較下如何穩定表現？"},
        {"num": 2, "title": "遠離網路焦慮：穩定自我價值波動"},
        {"num": 3, "title": "壓力下的抉擇：我會崩潰還是逆境成長？"},
        {"num": 4, "title": "團隊定位：我是領導者還是跟隨者？"},
    ]},
    {"num": 10, "icon": "🏁", "title": "啟動未來：我的終極定位藍圖", "sections": [
        {"num": 1, "title": "確認我的長期目標與堅持度"},
        {"num": 2, "title": "盤點智能組合：打造我的未來競爭力"},
        {"num": 3, "title": "降低升學風險，提升領導潛質"},
        {"num": 4, "title": "最終產出：我的升學與發展戰略圖"},
    ]},
]

# 青少年體驗版章節（對應 teen-report-app 的 0-indexed [0,2,6,9] → 1-indexed 1,3,7,10）
TEEN_TRIAL_CHAPTERS = {1, 3, 7, 10}


def get_chapters(report_type: str, variant: str) -> List[Dict]:
    """
    回傳指定報告類型 + 版本的章節清單

    Args:
        report_type: 'life_script' / 'child' / 'teen' / 'parent_child' / 'marital'
        variant:     'trial' / 'full' / 'vip'

    Returns:
        list of chapter dicts，每個含 num, icon, title, sections
    """
    if report_type == "teen":
        all_chapters = TEEN_CHAPTERS
        trial_set = TEEN_TRIAL_CHAPTERS
    elif report_type in ("life_script", "child"):
        all_chapters = LIFE_SCRIPT_CHAPTERS
        trial_set = TRIAL_CHAPTERS
    else:
        # parent_child / marital 之後從 HomeAnalysisReport / marital-report 接入
        all_chapters = LIFE_SCRIPT_CHAPTERS
        trial_set = TRIAL_CHAPTERS

    if variant == "trial":
        return [c for c in all_chapters if c["num"] in trial_set]
    return list(all_chapters)


def count_sections(chapters: List[Dict]) -> int:
    return sum(len(c["sections"]) for c in chapters)


# 中文數字
CH_NUMS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
SEC_NUMS = ["一", "二", "三", "四"]


def ch_zh(num: int) -> str:
    if 1 <= num <= 13:
        return CH_NUMS[num - 1]
    return str(num)


def sec_zh(num: int) -> str:
    if 1 <= num <= 4:
        return SEC_NUMS[num - 1]
    return str(num)
