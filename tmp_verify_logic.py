"""
驗證 report-app 的 JS patch 邏輯是否正確
直接從 index-CqHWGLJp.js 擷取並模擬執行關鍵判斷邏輯
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# ─── 1. 確認各 patch 是否真的在 JS 裡 ────────────────────────────────────────
print("=" * 60)
print("【第一步】確認 JS 中的關鍵字串")
print("=" * 60)

checks = {
    "L=9999（所有小節不截斷）":                 "L=9999",
    "L=1050（舊截斷，應該不存在）":              "?9999:1050",
    "q6 用 80 字 filter（新）":                 'filter((D,i,ar)=>{const s=(G||"").indexOf("第"+D+"大")',
    "q6 用 includes 判斷（舊，應不存在）":       'filter(D=>!G.includes("第"+D+"大")',
    "retry message 用 80 字 filter（新）":       'filter((r,i,ar)=>{const s=(G||"").indexOf("第"+r+"大")',
    "retry message 用 includes 判斷（舊）":      'filter(r=>!(G||"").includes("第"+r+"大")',
    "_chk5da 80字驗證 intact":                  'return(nx<0?a.length:nx)-s>=80})',
    "retry loop D<(x?5:3)（新）":               'D<(x?5:3)',
    "retry loop D<3（舊，應不存在）":            'for(let D=0;D<3;D++)',
}

all_ok = True
for label, pat in checks.items():
    found = pat in js
    should_exist = "應不存在" not in label and "舊" not in label
    if should_exist:
        status = "✅ 存在" if found else "❌ 不存在（patch 未套用！）"
        if not found:
            all_ok = False
    else:
        status = "❌ 仍然存在（舊邏輯未被替換！）" if found else "✅ 已被移除"
        if found:
            all_ok = False
    print(f"  {status}  ←  {label}")

print()

# ─── 2. 用 Python 模擬 JS 邏輯，驗證正確性 ────────────────────────────────────
print("=" * 60)
print("【第二步】用 Python 模擬 JS 的核心判斷邏輯")
print("=" * 60)

NUMS = ["一", "二", "三", "四", "五"]

def _chk5da(text: str) -> bool:
    """完整的 80 字閾值判斷（與 JS 一致）"""
    if not text:
        return False
    for i, r in enumerate(NUMS):
        s = text.find("第" + r + "大")
        if s < 0:
            return False
        if i < 4:
            nx = text.find("第" + NUMS[i+1] + "大", s + 1)
        else:
            nx = -1
        length = (len(text) if nx < 0 else nx) - s
        if length < 80:
            return False
    return True

def q6_old(text: str):
    """舊的 q6 filter：只看 '第X大' 是否存在"""
    return [r for r in NUMS if ("第" + r + "大") not in text]

def q6_new(text: str):
    """新的 q6 filter：用 80 字閾值（與 _chk5da 一致）"""
    result = []
    for i, r in enumerate(NUMS):
        s = (text or "").find("第" + r + "大")
        if s < 0:
            result.append(r)
            continue
        nx = (text or "").find("第" + NUMS[i+1] + "大", s + 1) if i < 4 else -1
        length = (len(text or "") if nx < 0 else nx) - s
        if length < 80:
            result.append(r)
    return result

# ─── 測試案例 ────────────────────────────────────────────────────────────────
def make_full_item(n, title, chars=160):
    """建立一個完整的項目（超過 80 字）"""
    body = f"這是第{n}大{title}的詳細說明，包含腦波數值分析與建議，字數充足超過八十字，確保品質。" * 3
    return f"第{n}大{title}｜{body[:chars]}"

def make_short_item(n, title):
    """建立一個只有標題的項目（不足 80 字）"""
    return f"第{n}大{title}｜（內容略）"

test_cases = [
    {
        "name": "✅ 正常：5 項都有 ≥80 字",
        "content": "\n".join([make_full_item(n, "優勢") for n in NUMS]),
        "expected_pass": True,
        "expected_q6": [],
    },
    {
        "name": "❌ 缺少第 4、5 項（完全沒有）",
        "content": "\n".join([make_full_item(n, "優勢") for n in NUMS[:3]]),
        "expected_pass": False,
        "expected_q6": ["四", "五"],
    },
    {
        "name": "❌ 第 4、5 項存在但不足 80 字（Gemini 只輸出了標題）",
        "content": "\n".join(
            [make_full_item(n, "優勢") for n in NUMS[:3]]
            + [make_short_item(n, "優勢") for n in NUMS[3:]]
        ),
        "expected_pass": False,
        "expected_q6": ["四", "五"],  # <── 這是以前舊邏輯抓不到的 bug 案例！
    },
    {
        "name": "⚠️  第 3 項只有 50 字（邊界案例）",
        "content": "\n".join(
            [make_full_item(n, "優勢") for n in ["一", "二"]]
            + [make_full_item("三", "優勢", chars=50)]
            + [make_full_item(n, "優勢") for n in ["四", "五"]]
        ),
        "expected_pass": False,
        "expected_q6": ["三"],
    },
]

print()
test_ok = True
for tc in test_cases:
    txt = tc["content"]
    chk = _chk5da(txt)
    q_old = q6_old(txt)
    q_new = q6_new(txt)
    
    chk_ok = chk == tc["expected_pass"]
    q6_ok  = q_new == tc["expected_q6"]
    old_bug = q_old != tc["expected_q6"]  # 舊邏輯是否有 bug
    
    print(f"  案例：{tc['name']}")
    print(f"    _chk5da()  → {chk}  （期待 {tc['expected_pass']}）  {'✅' if chk_ok else '❌ 錯誤！'}")
    print(f"    舊 q6 filter → {q_old}  {'⚠️  BUG：結果與 _chk5da 不符！' if old_bug else '（此案例舊邏輯偶然正確）'}")
    print(f"    新 q6 filter → {q_new}  （期待 {tc['expected_q6']}）  {'✅' if q6_ok else '❌ 錯誤！'}")
    
    if not chk_ok or not q6_ok:
        test_ok = False
    print()

# ─── 3. 文字截斷驗證 ──────────────────────────────────────────────────────────
print("=" * 60)
print("【第三步】確認 L=9999 截斷已移除")
print("=" * 60)
# Count how many times L=9999 appears vs any other L= pattern
import re
l_patterns = re.findall(r'L=k\|\|c===|L=9999|L=k\?', js)
print(f"  JS 中 L=9999 出現次數：{l_patterns.count('L=9999')}")
print(f"  JS 中 L=k||c=== 出現次數：{l_patterns.count('L=k||c===')} （應為 0）")

print()
print("=" * 60)
if all_ok and test_ok:
    print("✅ 所有驗證通過")
else:
    print("❌ 有驗證失敗，請檢查上方輸出")
print("=" * 60)
