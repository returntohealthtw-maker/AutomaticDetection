"""
八卦類型推算（Python 3 版）

提供 3 種推算方式：
    Bagua.calcType(brainColor, thetaMean)         - 用 Mind Color + theta 平均
    Bagua.calcBagua(brainColor, lowAlphaMean)     - 用 lowAlpha 對數機率值（推薦，準）
    Bagua.calcBaguaFromColors(top2_colors)        - 用 top 2 顏色組合
"""
import math
import scipy.stats as stats

from app.algorithms.brainwave import MindColorAlgorithm
from app.algorithms.data_stats import DATA_STATS


class BaguaTypes:
    def __init__(self, name=None, id=None):
        self.name = name
        self.id   = id

    def __repr__(self):
        return f"<Bagua {self.id} {self.name}>"


class Bagua:
    QIAN = BaguaTypes(name="乾", id="qian")
    DUI  = BaguaTypes(name="兌", id="dui")
    LI   = BaguaTypes(name="離", id="li")
    ZHEN = BaguaTypes(name="震", id="zhen")
    XUN  = BaguaTypes(name="巽", id="xun")
    KAN  = BaguaTypes(name="坎", id="kan")
    GEN  = BaguaTypes(name="艮", id="gen")
    KUN  = BaguaTypes(name="坤", id="kun")

    @classmethod
    def calcType(cls, brainColor, thetaMean):
        """方法 A：Mind Color + theta（thetaMean 是 0~1 的標準化值）"""
        if brainColor == MindColorAlgorithm.ORANGE:
            return cls.QIAN if thetaMean > 0.75 else cls.DUI
        elif brainColor == MindColorAlgorithm.GREEN:
            return cls.LI   if thetaMean > 0.75 else cls.ZHEN
        elif brainColor == MindColorAlgorithm.BLUE:
            return cls.XUN  if thetaMean > 0.75 else cls.KAN
        elif brainColor == MindColorAlgorithm.YELLOW:
            return cls.GEN  if thetaMean > 0.75 else cls.KUN
        return cls.KUN  # fallback

    @classmethod
    def calcBagua(cls, brainColor, lowAlphaMean):
        """方法 B：用 lowAlpha 對數值與人口分布計算 p 值（7 卦，向下相容）"""
        if lowAlphaMean <= 0:
            return cls.XUN  # fallback
        try:
            p_value = stats.norm.cdf(
                math.log10(lowAlphaMean),
                DATA_STATS["lowAlpha"]["mean"],
                DATA_STATS["lowAlpha"]["std"],
            )
        except (ValueError, ZeroDivisionError):
            return cls.XUN

        if   p_value < 0.125: return cls.QIAN
        elif p_value < 0.250: return cls.DUI
        elif p_value < 0.375: return cls.ZHEN
        elif p_value < 0.500: return cls.XUN
        elif p_value < 0.625: return cls.KAN
        elif p_value < 0.750: return cls.GEN
        else:                 return cls.KUN

    @classmethod
    def calcBaguaWithLi(cls, lowAlphaMean, thetaMean):
        """
        方法 B+：8 卦系統（含離卦），與前端 _etBaguaMBTI(useLi=True) 完全一致。

        在 laPct 0.250~0.375 帶，加入 theta 判斷：
            theta_p > 0.5 → 離卦（LI）→ INFJ / INFP
            theta_p ≤ 0.5 → 震卦（ZHEN）→ ENFJ / ENFP

        所有其他區間行為與 calcBagua 相同。
        報告生成（成人 & 兒童）應使用此方法以確保與 APP 顯示一致。
        """
        if lowAlphaMean <= 0:
            return cls.XUN
        try:
            la_p = stats.norm.cdf(
                math.log10(lowAlphaMean),
                DATA_STATS["lowAlpha"]["mean"],
                DATA_STATS["lowAlpha"]["std"],
            )
        except (ValueError, ZeroDivisionError):
            return cls.XUN

        if   la_p < 0.125: return cls.QIAN
        elif la_p < 0.250: return cls.DUI
        elif la_p < 0.375:
            # 離/震 分割：theta 百分位 > 0.5 → 離卦（INFJ/INFP）
            if thetaMean > 0:
                try:
                    th_p = stats.norm.cdf(
                        math.log10(thetaMean),
                        DATA_STATS["lowAlpha"]["mean"],
                        DATA_STATS["lowAlpha"]["std"],
                    )
                    return cls.LI if th_p > 0.5 else cls.ZHEN
                except (ValueError, ZeroDivisionError):
                    pass
            return cls.ZHEN
        elif la_p < 0.500: return cls.XUN
        elif la_p < 0.625: return cls.KAN
        elif la_p < 0.750: return cls.GEN
        else:              return cls.KUN

    @classmethod
    def calcBaguaFromColors(cls, colors):
        """方法 C：用 top 2 顏色組合"""
        if len(colors) < 2:
            return cls.XUN
        c0, c1 = colors[0], colors[1]
        Y, G, B, O = (
            MindColorAlgorithm.YELLOW,
            MindColorAlgorithm.GREEN,
            MindColorAlgorithm.BLUE,
            MindColorAlgorithm.ORANGE,
        )

        def pair(a, b):
            return (c0 == a and c1 == b) or (c0 == b and c1 == a)

        if   pair(Y, G):                      return cls.QIAN
        elif c0 == Y and c1 == Y:             return cls.DUI
        elif pair(Y, B):                      return cls.LI
        elif pair(G, B):                      return cls.ZHEN
        elif c0 == O and c1 == O:             return cls.XUN
        elif pair(O, G):                      return cls.KAN
        elif pair(O, B):                      return cls.KUN
        else:                                 return cls.XUN
