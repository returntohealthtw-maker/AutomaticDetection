"""
MBTI 16 型推算（Python 3 版）

兩種推算路徑：
    Personality.calcPersonality(bagua, colors, theta, beta)
        - 用 八卦 + 顏色 + theta/beta 比較

    Personality.getPersonalityFromBagua(bagua, thetaMean)
        - 用 八卦 + theta 對數機率值（推薦：跟 Bagua.calcBagua 一致的數理基礎）

附帶 calculateMBTIGroup：把同群組 4 個 MBTI 加分。
"""
import math
import scipy.stats as stats

from app.algorithms.bagua import Bagua
from app.algorithms.brainwave import MindColorAlgorithm
from app.algorithms.data_stats import DATA_STATS


class PersonalityType:
    def __init__(self, name=None, id=None, name_zh=None):
        self.name    = name      # 英文外號（NERIS 16 personalities 命名）
        self.id      = id        # 4 字母 e.g. INTJ
        self.name_zh = name_zh   # 繁中外號

    def __repr__(self):
        return f"<MBTI {self.id}>"


class Personality:
    INTJ = PersonalityType(name="ARCHITECT",     id="INTJ", name_zh="建築師")
    INTP = PersonalityType(name="LOGICIAN",      id="INTP", name_zh="邏輯學家")
    ENTJ = PersonalityType(name="COMMANDER",     id="ENTJ", name_zh="指揮官")
    ENTP = PersonalityType(name="DEBATER",       id="ENTP", name_zh="辯論家")
    INFJ = PersonalityType(name="ADVOCATE",      id="INFJ", name_zh="提倡者")
    INFP = PersonalityType(name="MEDIATOR",      id="INFP", name_zh="調停者")
    ENFJ = PersonalityType(name="PROTAGONIST",   id="ENFJ", name_zh="主人公")
    ENFP = PersonalityType(name="CAMPAIGNER",    id="ENFP", name_zh="競選者")
    ISTJ = PersonalityType(name="LOGISTICIAN",   id="ISTJ", name_zh="物流師")
    ISFJ = PersonalityType(name="DEFENDER",      id="ISFJ", name_zh="守衛者")
    ESTJ = PersonalityType(name="EXECUTIVE",     id="ESTJ", name_zh="總經理")
    ESFJ = PersonalityType(name="CONSUL",        id="ESFJ", name_zh="執政官")
    ISTP = PersonalityType(name="VIRTUOSO",      id="ISTP", name_zh="鑑賞家")
    ISFP = PersonalityType(name="ADVENTURER",    id="ISFP", name_zh="探險家")
    ESTP = PersonalityType(name="ENTREPRENEUR",  id="ESTP", name_zh="企業家")
    ESFP = PersonalityType(name="ENTERTAINER",   id="ESFP", name_zh="表演者")

    personalityGroups = [
        [INFP, ISFP, ENFJ, ESFJ],   # 外交官-情感主導
        [ESFP, ESTP, ISTJ, ISFJ],   # 行動派 / 守護者
        [ISTP, INTP, ENTJ, ESTJ],   # 分析家
        [ENTP, ENFP, INFJ, INTJ],   # 革新家 / 直覺主導
    ]

    @classmethod
    def calcPersonality(cls, bagua, colors, theta, beta):
        """方法 A：用八卦 + 主色 / theta-beta 比較"""
        if bagua == Bagua.QIAN:
            return cls.ENTJ if colors[0] == MindColorAlgorithm.GREEN else cls.ESTJ
        elif bagua == Bagua.DUI:
            return cls.ISFJ if beta > theta else cls.ISTJ
        elif bagua == Bagua.LI:
            return cls.ENFJ if colors[0] == MindColorAlgorithm.BLUE else cls.ESFJ
        elif bagua == Bagua.ZHEN:
            return cls.INFJ if colors[0] == MindColorAlgorithm.BLUE else cls.INTJ
        elif bagua == Bagua.XUN:
            return cls.ESFP if beta > theta else cls.ESTP
        elif bagua == Bagua.KAN:
            return cls.INTP if colors[0] == MindColorAlgorithm.GREEN else cls.ISTP
        elif bagua == Bagua.GEN:
            return cls.ENFP if colors[0] == MindColorAlgorithm.BLUE else cls.ENTP
        else:  # KUN
            return cls.INFP if colors[0] == MindColorAlgorithm.BLUE else cls.ISFP

    @classmethod
    def getPersonalityFromBagua(cls, bagua, thetaMean):
        """方法 B：用 theta 對數機率值切 16 型（推薦）"""
        if thetaMean <= 0:
            return cls.INTP  # fallback
        try:
            theta_p = stats.norm.cdf(
                math.log10(thetaMean),
                DATA_STATS["lowAlpha"]["mean"],
                DATA_STATS["lowAlpha"]["std"],
            )
        except (ValueError, ZeroDivisionError):
            return cls.INTP

        high = theta_p > 0.5
        mapping = {
            id(Bagua.QIAN): (cls.INTJ, cls.INTP),
            id(Bagua.DUI):  (cls.ENTJ, cls.ENTP),
            id(Bagua.LI):   (cls.INFJ, cls.INFP),
            id(Bagua.ZHEN): (cls.ENFJ, cls.ENFP),
            id(Bagua.XUN):  (cls.ISTJ, cls.ISFJ),
            id(Bagua.KAN):  (cls.ESTJ, cls.ESFJ),
            id(Bagua.GEN):  (cls.ISTP, cls.ISFP),
            id(Bagua.KUN):  (cls.ESTP, cls.ESFP),
        }
        pair = mapping.get(id(bagua))
        if not pair:
            return cls.INTP
        return pair[0] if high else pair[1]

    @classmethod
    def calculateMBTIGroup(cls, mbti, personalities):
        """同群組加分（主型 +2、同群其他 +1），用於雷達圖呈現"""
        group_index = 0
        for i in range(len(personalities)):
            for j in range(len(personalities[i])):
                if personalities[i][j]["personality"] == mbti:
                    group_index = i
                    break
        for j in range(len(personalities[group_index])):
            points = 2 if personalities[group_index][j]["personality"] == mbti else 1
            personalities[group_index][j]["points"] += points
        return personalities
