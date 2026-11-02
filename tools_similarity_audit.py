# -*- coding: utf-8 -*-
"""
報告文字相似度稽核（跨人比較）。

輸入：多個 gen_*.json（rp_gen.js 產出：{"name":..., "texts": {"1-1": "...", ...}}）
輸出：同一小節在不同人之間的字元 n-gram Jaccard、共用長片段數，以及「跨人反覆出現的套話片段」。
先把姓名與數字、標點正規化掉，避免被姓名/數值本身干擾。

用法：python tools_similarity_audit.py <label> a.json b.json c.json [--phrases N]
"""
import io, json, re, sys, itertools, collections

sys.stdout.reconfigure(encoding="utf-8")


def norm(t, name):
    t = t.replace(name, "").replace(name[1:] if len(name) > 1 else name, "")
    t = re.sub(r"[0-9０-９]+(\.[0-9]+)?", "#", t)
    t = re.sub(r"[\s，。、；：「」『』（）()！？!?…—\-－・,.:;\"'％%↑↓↔＝=]+", "", t)
    return t


def grams(t, n):
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def jacc(a, b):
    return len(a & b) / max(1, len(a | b))


def main():
    label = sys.argv[1]
    files = [a for a in sys.argv[2:] if a.endswith(".json")]
    topn = 25
    if "--phrases" in sys.argv:
        topn = int(sys.argv[sys.argv.index("--phrases") + 1])
    data = [json.load(io.open(f, encoding="utf-8")) for f in files]
    keys = sorted(set.intersection(*[set(d["texts"]) for d in data]), key=lambda k: tuple(int(x) for x in k.split("-")))
    print(f"=== {label}  人數={len(data)}  小節={len(keys)} ===")
    tot4, tot8, cnt = 0, 0, 0
    per_key = []
    for k in keys:
        ts = [norm(d["texts"][k], d["name"]) for d in data]
        if any(t.startswith("ERROR") or len(t) < 50 for t in ts):
            continue
        j4s, j8s = [], []
        for x, y in itertools.combinations(ts, 2):
            j4s.append(jacc(grams(x, 4), grams(y, 4)))
            j8s.append(jacc(grams(x, 8), grams(y, 8)))
        per_key.append((k, sum(j4s) / len(j4s), sum(j8s) / len(j8s)))
        tot4 += sum(j4s) / len(j4s); tot8 += sum(j8s) / len(j8s); cnt += 1
    for k, a, b in per_key:
        print(f"  {k:>5}  4-gram Jaccard={a:.3f}  8-gram Jaccard={b:.3f}")
    print(f"  平均   4-gram={tot4 / cnt:.3f}   8-gram={tot8 / cnt:.3f}")
    # 跨人套話：10 字片段在 >=2 個人的文字中出現，且跨 >=2 個小節
    n = 10
    seen = collections.defaultdict(lambda: {"people": set(), "keys": set()})
    for d in data:
        for k in keys:
            t = norm(d["texts"][k], d["name"])
            for g in grams(t, n):
                seen[g]["people"].add(d["name"]); seen[g]["keys"].add(k)
    stock = [(g, v) for g, v in seen.items() if len(v["people"]) >= 2 and len(v["keys"]) >= 2]
    print(f"\n  跨人且跨小節重複的 {n} 字片段數：{len(stock)}")
    # 合併成較長片段方便閱讀（取彼此不重疊的前 N 個）
    stock.sort(key=lambda x: (-len(x[1]["keys"]), x[0]))
    shown = []
    for g, v in stock:
        if any(g in s or s in g for s in shown):
            continue
        shown.append(g)
        if len(shown) >= topn:
            break
    for s in shown:
        print("   ·", s)


main()
