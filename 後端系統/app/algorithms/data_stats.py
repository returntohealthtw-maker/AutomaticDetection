"""
人口腦波對數值 mean / std 標準化常數

來源：BrainDNA evaluationReport.py 中的 Report.DATA_STATS。
這是從上千人腦波樣本計算出的「對數轉換後」常數，作為八卦 / MBTI 推算的基準分布。

使用方式：
    z = (math.log10(個人 lowAlpha 平均) - DATA_STATS['lowAlpha']['mean']) / DATA_STATS['lowAlpha']['std']
    p = scipy.stats.norm.cdf(z)
"""

DATA_STATS = {
    "delta":     {"mean": 5.29835995039, "std": 0.542447565538},
    "theta":     {"mean": 4.72538897932, "std": 0.441840459259},
    "lowAlpha":  {"mean": 4.07285436418, "std": 0.424115475935},
    "highAlpha": {"mean": 4.09023791618, "std": 0.376780766056},
    "lowBeta":   {"mean": 4.02628991082, "std": 0.404178025673},
    "highBeta":  {"mean": 4.08907476245, "std": 0.392740498864},
    "lowGamma":  {"mean": 3.7574299841,  "std": 0.426077247618},
    "midGamma":  {"mean": 3.75332489124, "std": 0.628883941715},
}

DATA_VALUES = [
    "delta",
    "theta",
    "lowAlpha",
    "highAlpha",
    "lowBeta",
    "highBeta",
    "lowGamma",
    "midGamma",
]
