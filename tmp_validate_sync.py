"""
驗證前端 JavaScript _BDNA_PR 與後端 Python _PROP_RANGE 是否完全一致。
若有任何不符，直接列出差異並 exit(1)。
"""
import re, sys, os

BACKEND_FILE  = os.path.join(os.path.dirname(__file__), "後端系統/app/services/braindna_algorithms.py")
FRONTEND_FILE = os.path.join(os.path.dirname(__file__), "後端系統/static-app/app_prototype.html")

# ── 讀後端 Python _PROP_RANGE ────────────────────────────────────────────────
py_text = open(BACKEND_FILE, encoding="utf-8").read()
# 擷取 _PROP_RANGE = { ... } 區塊
m = re.search(r'_PROP_RANGE\s*=\s*\{([^}]+)\}', py_text)
if not m:
    sys.exit("[ERROR] 找不到 Python _PROP_RANGE")

py_range = {}
for line in m.group(1).splitlines():
    hit = re.search(r'"(r_\w+)"\s*:\s*\(([\d.]+),\s*([\d.]+)\)', line)
    if hit:
        py_range[hit.group(1)] = (float(hit.group(2)), float(hit.group(3)))

# ── 讀前端 JavaScript _BDNA_PR ───────────────────────────────────────────────
js_text = open(FRONTEND_FILE, encoding="utf-8").read()
m2 = re.search(r'const _BDNA_PR\s*=\s*\{([^}]+)\}', js_text)
if not m2:
    sys.exit("[ERROR] 找不到 JS _BDNA_PR")

js_range = {}
for hit in re.finditer(r'(r_\w+):\[([\d.]+),([\d.]+)\]', m2.group(1)):
    js_range[hit.group(1)] = (float(hit.group(2)), float(hit.group(3)))

# ── 比對 ─────────────────────────────────────────────────────────────────────
KEYS = ["r_delta","r_theta","r_lalpha","r_halpha","r_lbeta","r_hbeta","r_lgamma","r_hgamma"]
LABEL = {"r_delta":"Delta","r_theta":"Theta","r_lalpha":"Low α","r_halpha":"High α",
         "r_lbeta":"Low β","r_hbeta":"High β","r_lgamma":"Low γ","r_hgamma":"High γ"}

print(f"{'頻段':<10} {'Python level1':>14} {'JS level1':>10} {'Python level2':>14} {'JS level2':>10} {'狀態':>6}")
print("-" * 70)

all_ok = True
for k in KEYS:
    py = py_range.get(k, (None, None))
    js = js_range.get(k, (None, None))
    ok = (py[0] == js[0] and py[1] == js[1])
    status = "OK" if ok else "MISMATCH"
    if not ok:
        all_ok = False
    print(f"  {LABEL[k]:<8}  {py[0]:>12}  {js[0]:>9}  {py[1]:>12}  {js[1]:>9}  {status}")

print()
if all_ok:
    print("PASS: frontend and backend _PROP_RANGE are identical")
else:
    print("FAIL: mismatch detected, please sync and rerun")
    sys.exit(1)
