"""
BrainDNA 腦波核心演算法（Python 3 版）

包含：
    MindColorAlgorithm    - 4 色腦人（橘/綠/藍/黃）
    MindBalanceAlgorithm  - 身心平衡分數
    MindEnergyAlgorithm   - 腦力能量分數
    MindStressAlgorithm   - 壓力指數
    MindValueAlgorithm    - 平均/中位數/比例 工具
    MindValueCalcHelper   - 多頻段計算助手
    MindValueTop          - 各頻段上限值
    ReportResult          - 報告結果容器（calcColor / calcPie）
"""
import math
from collections import OrderedDict
from operator import itemgetter


# ─── 身心平衡 ────────────────────────────────────────────────────────────────

class MindBalanceAlgorithm:
    ZONE_ATTENTION  = [0, 40, 70, 100]
    ZONE_MEDITATION = [0, 40, 70, 100]
    PRIORITY_FACTOR_1 = 30
    PRIORITY_FACTOR_2 = 50
    PRIORITY_FACTOR_3 = 20

    @classmethod
    def calc(cls, attention, meditation):
        zone_a = cls._calc_zone(attention,  cls.ZONE_ATTENTION)
        zone_m = cls._calc_zone(meditation, cls.ZONE_MEDITATION)
        return int(
            cls._factor1(zone_a, zone_m)
            + cls._factor2(zone_a, zone_m)
            + cls._factor3(zone_a, zone_m)
        )

    @staticmethod
    def _calc_zone(values, threshold):
        zone = [0] * (len(threshold) - 1)
        for v in values:
            for j in range(1, len(threshold)):
                if threshold[j - 1] <= v <= threshold[j]:
                    zone[j - 1] += 1
                    break
        return zone

    @staticmethod
    def _factor1(v1, v2):
        f = math.fabs((v1[1] + v1[2]) - (v2[1] + v2[2]))
        return (30.0 - f) / 30 * 100 * 0.3

    @staticmethod
    def _factor2(v1, v2):
        f = math.fabs(v1[0] - v2[0]) + math.fabs(v1[1] - v2[1]) + math.fabs(v1[2] - v2[2])
        return (60.0 - f) / 60 * 100 * 0.5

    @staticmethod
    def _factor3(v1, v2):
        f = v1[2] + v2[2]
        return f / 60.0 * 100 * 0.2


# ─── 腦力能量 ────────────────────────────────────────────────────────────────

class MindEnergyAlgorithm:
    ZONE_ATTENTION  = [0, 40, 70, 100]
    ZONE_MEDITATION = [0, 40, 70, 100]

    @classmethod
    def calc(cls, attention, meditation):
        zone_a = cls._calc_zone(attention,  cls.ZONE_ATTENTION)
        zone_m = cls._calc_zone(meditation, cls.ZONE_MEDITATION)
        return int(cls._factor1(zone_a, zone_m) + cls._factor2(zone_a, zone_m))

    @staticmethod
    def _calc_zone(values, threshold):
        zone = [0] * (len(threshold) - 1)
        for v in values:
            for j in range(1, len(threshold)):
                if threshold[j - 1] <= v <= threshold[j]:
                    zone[j - 1] += 1
                    break
        return zone

    @staticmethod
    def _factor1(v1, v2):
        f = v1[2] + v2[2]
        return f / 60.0 * 100 * 0.5

    @staticmethod
    def _factor2(v1, v2):
        s1 = v1[0] + v1[1] + v1[2]
        s2 = v2[0] + v2[1] + v2[2]
        if s1 == 0 or s2 == 0:
            return 0
        f = 100 * (v1[0] / s1 + v2[0] / s2)
        return (100 - f * 0.5) * 0.5


# ─── 壓力指數 ────────────────────────────────────────────────────────────────

class MindStressAlgorithm:
    THR_MIDGAMMA_TOP    = 6000
    THR_LOWALPHA_TOP    = 25000
    THR_LOWALPHA_BOTTOM = 4000
    THR_MIDGAMMA_BOTTOM = 2000
    PROPORTION_MIDGAMMA = 50
    PROPORTION_LOWALPHA = 50

    @classmethod
    def calc(cls, midGamma, lowAlpha):
        ave_mg = cls._calc_ave(midGamma, cls.THR_MIDGAMMA_BOTTOM, cls.THR_MIDGAMMA_TOP)
        ave_la = cls._calc_ave(lowAlpha, cls.THR_LOWALPHA_BOTTOM, cls.THR_LOWALPHA_TOP)
        pt_mg  = cls._calc_percent(ave_mg, cls.THR_MIDGAMMA_BOTTOM, cls.THR_MIDGAMMA_TOP)
        pt_la  = cls._calc_percent(ave_la, cls.THR_LOWALPHA_BOTTOM, cls.THR_LOWALPHA_TOP)
        return int(cls.PROPORTION_MIDGAMMA * pt_mg + cls.PROPORTION_LOWALPHA * pt_la)

    @staticmethod
    def _calc_ave(values, bottom, top):
        if not values:
            return 0
        s = sum(top if i > top else (bottom if i < bottom else i) for i in values)
        return s / len(values)

    @staticmethod
    def _calc_percent(value, bottom, top):
        return (value - bottom) / (top - bottom)


# ─── 4 色腦人 ────────────────────────────────────────────────────────────────

class MindColorAlgorithm:
    ORANGE = 0
    GREEN  = 1
    BLUE   = 2
    YELLOW = 3

    colorTypes = OrderedDict([
        ("orange", 0),
        ("green",  1),
        ("blue",   2),
        ("yellow", 3),
    ])

    colorRanges = {
        "orange": ((25, 40), (30, 55)),
        "green":  ((20, 45), (10, 45)),
        "blue":   ((30, 55), (40, 65)),
        "yellow": ((15, 35), (0, 40)),
    }
    colorCenters = {
        "orange": (32.5, 42.5),
        "green":  (32.5, 27.5),
        "blue":   (42.5, 52.5),
        "yellow": (25,   20),
    }

    @classmethod
    def calc(cls, highAlpha, lowAlpha, highBeta, lowBeta, lowGamma, midGamma):
        alpha = highAlpha + lowAlpha
        beta  = highBeta  + lowBeta
        gamma = lowGamma  + midGamma
        if alpha <= 0 or beta <= 0:
            return 0

        f1 = (gamma / alpha) * 100
        f2 = (gamma / beta)  * 100

        color_key = None
        min_dist  = 999
        for k, center in cls.colorCenters.items():
            d = math.sqrt((center[0] - f1) ** 2 + (center[1] - f2) ** 2)
            if d < min_dist:
                min_dist = d
                color_key = k
        return cls.colorTypes[color_key] if color_key else 0

    @classmethod
    def factorFirstRange(cls, color, factor):
        bands = {
            cls.colorTypes["blue"]:   (0.3,  0.55),
            cls.colorTypes["green"]:  (0.2,  0.45),
            cls.colorTypes["orange"]: (0.25, 0.4),
            cls.colorTypes["yellow"]: (0.15, 0.35),
        }
        if color not in bands:
            return False
        lo, hi = bands[color]
        return lo < factor < hi

    @classmethod
    def factorSecondRange(cls, color, factor):
        bands = {
            cls.colorTypes["blue"]:   (0.4, 0.65),
            cls.colorTypes["green"]:  (0.1, 0.45),
            cls.colorTypes["orange"]: (0.3, 0.55),
            cls.colorTypes["yellow"]: (0.0, 0.4),
        }
        if color not in bands:
            return False
        lo, hi = bands[color]
        return lo < factor < hi

    @classmethod
    def calcForWeights(cls, highAlpha, lowAlpha, highBeta, lowBeta, lowGamma, midGamma, weights):
        alpha = highAlpha + lowAlpha
        beta  = highBeta  + lowBeta
        gamma = lowGamma  + midGamma
        if alpha == 0 or beta == 0:
            return 0
        f1 = gamma / alpha
        f2 = gamma / beta
        meets  = [0, 0, 0, 0]
        meets2 = []

        for value in cls.colorTypes.values():
            if cls.factorFirstRange(value, f1):
                meets[value] += 1
                meets2.append(value)
        if len(meets2) == 1:
            return meets2[0]

        for value in cls.colorTypes.values():
            if not cls.factorFirstRange(value, f2):
                meets[value] -= 1

        # Python 3 OrderedDict.values() 不支援 indexing，先轉 list
        color_values = list(cls.colorTypes.values())
        while weights > 0:
            weights = weights // 10
            index = weights % 10
            if 0 <= index < len(meets) and meets[index] > 0:
                return color_values[index]
        return color_values[0]

    @classmethod
    def sortColor(cls, brainColors):
        colors = [
            {"color": cls.ORANGE, "count": 0},
            {"color": cls.GREEN,  "count": 0},
            {"color": cls.BLUE,   "count": 0},
            {"color": cls.YELLOW, "count": 0},
        ]
        for bc in brainColors:
            for item in colors:
                if bc == item["color"]:
                    item["count"] += 1
                    break
        colors = sorted(colors, key=itemgetter("count"), reverse=True)
        return [c["color"] for c in colors]


# ─── MindValue 工具集 ────────────────────────────────────────────────────────

class MindValueAlgorithm:
    THRESHOLD_ALPHA_BETA = 120000
    THRESHOLD_THETA      = 90000

    @classmethod
    def average(cls, arr):
        if not arr:
            return 0
        return sum(arr) / len(arr)

    @classmethod
    def proportion(cls, arr, columnSumArray):
        if not arr:
            return 0
        ans = 0.0
        for i, v in enumerate(arr):
            if columnSumArray[i] == 0:
                ans += float(v / 1)
            else:
                ans += float(v) / float(columnSumArray[i])
        return ans / len(arr)

    @classmethod
    def median(cls, arr):
        if not arr:
            return 0
        arr = sorted(arr)
        mid = len(arr) // 2
        if len(arr) % 2 == 0:
            return (arr[mid - 1] + arr[mid]) / 2
        return arr[mid]

    @classmethod
    def geoMean(cls, values):
        if not values:
            return 0
        sumlog = 0
        positive_count = 0
        for v in values:
            if v > 0:
                sumlog += math.log(v, math.e)
                positive_count += 1
        if positive_count == 0:
            return 0
        return math.exp(sumlog / len(values))

    @classmethod
    def deNoise(cls, arr, mn=0.0, mx=0.0):
        gm = cls.geoMean(arr)
        if mx == 0:
            mx = 3 * gm
        new_arr = [x for x in arr if mn <= x < mx]
        return new_arr, mx

    @classmethod
    def proportionRange(cls, value, level1, level2):
        if level1 > level2 or level1 < 0 or value <= 0:
            return 0
        if value >= level2:
            return 1
        if value <= level1:
            return (value / level1) * 0.5
        return ((value - level1) / (level2 - level1)) * 0.5 + 0.5

    @classmethod
    def getArray(cls, arr, key):
        return [item[key] for item in arr]

    @classmethod
    def normalizeProportions(cls, arr, maxCount):
        total = sum(arr)
        if total == 0:
            return [0] * len(arr)
        return [int(float(x) / float(total) * maxCount) for x in arr]

    @classmethod
    def calcBand(cls, mindArray):
        index = 0
        score_best = 0
        for i in range(len(mindArray)):
            helper = MindValueCalcHelper(MindValueCalcHelper.Algorithm["proportion"])
            section = mindArray[i]
            delta     = cls.getArray(section, "delta")
            highAlpha = cls.getArray(section, "highAlpha")
            lowAlpha  = cls.getArray(section, "lowAlpha")
            highBeta  = cls.getArray(section, "highBeta")
            lowBeta   = cls.getArray(section, "lowBeta")
            lowGamma  = cls.getArray(section, "lowGamma")
            midGamma  = cls.getArray(section, "midGamma")
            theta     = cls.getArray(section, "theta")
            helper.calcColumnSumArray(delta, highAlpha, lowAlpha, highBeta, lowBeta, lowGamma, midGamma, theta)
            helper.calcLowGamma(lowGamma)
            if helper.lowGamma > score_best:
                score_best = helper.lowGamma
                index = i
        return index

    @classmethod
    def calcMindPie(cls, arr):
        s = [0, 0, 0]
        for v in arr:
            if v > 70:
                s[2] += 1
            elif v > 40:
                s[1] += 1
            else:
                s[0] += 1
        total = len(arr) or 1
        return [int(s[i] * 100.0 / total + 0.5) for i in range(3)]

    @classmethod
    def filterBands(cls, arr):
        filtered = []
        for section in arr:
            new_section = []
            for row in section:
                valid = True
                if row["theta"] > cls.THRESHOLD_THETA:
                    valid = False
                ab = row["highAlpha"] + row["lowAlpha"] + row["highBeta"] + row["lowBeta"]
                if ab > cls.THRESHOLD_ALPHA_BETA:
                    valid = False
                if valid:
                    new_section.append(row)
            filtered.append(new_section)
        return filtered


# ─── 各頻段上限 ──────────────────────────────────────────────────────────────

class MindValueTop:
    mDelta     = 98000
    mLowAlpha  = 50000
    mHighAlpha = 50000
    mLowBeta   = 50000
    mHighBeta  = 50000
    mLowGamma  = 10000
    mMidGamma  = 10000
    mTheta     = 98000

    @classmethod
    def delta(cls, v):     return cls.mDelta     if v > cls.mDelta     else v
    @classmethod
    def lowAlpha(cls, v):  return cls.mLowAlpha  if v > cls.mLowAlpha  else v
    @classmethod
    def highAlpha(cls, v): return cls.mHighAlpha if v > cls.mHighAlpha else v
    @classmethod
    def lowBeta(cls, v):   return cls.mLowBeta   if v > cls.mLowBeta   else v
    @classmethod
    def highBeta(cls, v):  return cls.mHighBeta  if v > cls.mHighBeta  else v
    @classmethod
    def lowGamma(cls, v):  return cls.mLowGamma  if v > cls.mLowGamma  else v
    @classmethod
    def midGamma(cls, v):  return cls.mMidGamma  if v > cls.mMidGamma  else v
    @classmethod
    def theta(cls, v):     return cls.mTheta     if v > cls.mTheta     else v


# ─── 多頻段計算助手 ──────────────────────────────────────────────────────────

class MindValueCalcHelper:
    Algorithm = {"average": 0, "proportion": 1, "median": 2}

    def __init__(self, algorithm):
        self.type = algorithm
        self.attention  = 0.0
        self.meditation = 0.0
        self.delta      = 0.0
        self.theta      = 0.0
        self.lowAlpha   = 0.0
        self.highAlpha  = 0.0
        self.lowBeta    = 0.0
        self.highBeta   = 0.0
        self.lowGamma   = 0.0
        self.midGamma   = 0.0
        self.columnSumArray = []

    def calcColumnSumArray(self, delta, highAlpha, lowAlpha, highBeta, lowBeta, lowGamma, midGamma, theta):
        n = len(delta)
        self.columnSumArray = [
            delta[i] + highAlpha[i] + lowAlpha[i] + highBeta[i] + lowBeta[i]
            + lowGamma[i] + midGamma[i] + theta[i]
            for i in range(n)
        ]

    def _calc_value(self, arr):
        if self.type == self.Algorithm["average"]:
            return MindValueAlgorithm.average(arr)
        if self.type == self.Algorithm["median"]:
            return MindValueAlgorithm.median(arr)
        if self.type == self.Algorithm["proportion"]:
            return MindValueAlgorithm.proportion(arr, self.columnSumArray)
        return 0.0

    def calcDelta(self, arr):
        capped = [MindValueTop.delta(v) for v in arr]
        self.delta = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.delta = MindValueAlgorithm.proportionRange(self.delta, 0.6, 0.8)

    def calcHighAlpha(self, arr):
        capped = [MindValueTop.highAlpha(v) for v in arr]
        self.highAlpha = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.highAlpha = MindValueAlgorithm.proportionRange(self.highAlpha, 0.1, 0.2)

    def calcLowAlpha(self, arr):
        capped = [MindValueTop.lowAlpha(v) for v in arr]
        self.lowAlpha = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.lowAlpha = MindValueAlgorithm.proportionRange(self.lowAlpha, 0.1, 0.2)

    def calcHighBeta(self, arr):
        capped = [MindValueTop.highBeta(v) for v in arr]
        self.highBeta = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.highBeta = MindValueAlgorithm.proportionRange(self.highBeta, 0.05, 0.1)

    def calcLowBeta(self, arr):
        capped = [MindValueTop.lowBeta(v) for v in arr]
        self.lowBeta = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.lowBeta = MindValueAlgorithm.proportionRange(self.lowBeta, 0.05, 0.1)

    def calcLowGamma(self, arr):
        capped = [MindValueTop.lowGamma(v) for v in arr]
        self.lowGamma = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.lowGamma = MindValueAlgorithm.proportionRange(self.lowGamma, 0.03, 0.06)

    def calcMidGamma(self, arr):
        capped = [MindValueTop.midGamma(v) for v in arr]
        self.midGamma = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.midGamma = MindValueAlgorithm.proportionRange(self.midGamma, 0.03, 0.06)

    def calcTheta(self, arr):
        capped = [MindValueTop.theta(v) for v in arr]
        self.theta = self._calc_value(capped)
        if self.type == self.Algorithm["proportion"]:
            self.theta = MindValueAlgorithm.proportionRange(self.theta, 0.15, 0.3)


# ─── 報告結果容器（含 calcColor / calcPie）──────────────────────────────────

class ReportResult:
    def __init__(self):
        self.attentionIntArray  = []
        self.meditationIntArray = []
        self.mindColor          = 0
        self.mindColorList      = []

    def calcPie(self, mindArray):
        score_best = 0
        for item in mindArray:
            score = 0
            attention_arr  = []
            meditation_arr = []
            for row in item:
                attention_arr.append(row.attention if hasattr(row, "attention") else row["attention"])
                meditation_arr.append(row.meditation if hasattr(row, "meditation") else row["meditation"])
                if attention_arr[-1] > 40:
                    score += 1
                if meditation_arr[-1] > 40:
                    score += 1
            if score > score_best:
                score_best = score
                self.attentionIntArray  = attention_arr
                self.meditationIntArray = meditation_arr

    def calcColor(self, mindArray, order, than, countY, countB, countG):
        # orange, green, blue, yellow
        self.mindColorList = []
        mind_color_count = [0, 0, 0, 0]
        count = [0, countG, countB, countY]
        for item in mindArray:
            ha = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "highAlpha"))
            la = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "lowAlpha"))
            hb = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "highBeta"))
            lb = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "lowBeta"))
            lg = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "lowGamma"))
            mg = MindValueAlgorithm.average(MindValueAlgorithm.getArray(item, "midGamma"))
            color_index = MindColorAlgorithm.calcForWeights(ha, la, hb, lb, lg, mg, order)
            mind_color_count[color_index] += 1
            self.mindColorList.append(color_index)

        for i in range(len(mind_color_count)):
            if mind_color_count[i] < count[i]:
                mind_color_count[i] = 0

        if mind_color_count[2] == 0 and mind_color_count[3] == 0 and mind_color_count[1] == 0:
            return self.mindColorList[0] if self.mindColorList else 0

        mind_color_count[0] = 0
        index = [i for i in range(len(mind_color_count)) if mind_color_count[i] != 0]

        if len(index) == 1:
            self.mindColor = index[0]
        elif len(index) >= 2:
            if self._than_to_bool(than, index[0], index[1]):
                self.mindColor = index[0]
            else:
                self.mindColor = index[1]
        return self.mindColor

    @staticmethod
    def _than_to_bool(than, color1, color2):
        color2_mask = 1 << color2
        i = (than >> (4 * color1)) & 0xF
        return (i & color2_mask) > 0
