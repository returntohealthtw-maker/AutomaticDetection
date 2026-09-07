import requests, sys, re
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

# 拉最新 HTML 確認有無 _showSubjectDetail
r = requests.get(f'{BASE}/app', timeout=15, verify=False)
html = r.text
print(f"GET /app: HTTP {r.status_code}, size={len(html)}")

# 確認關鍵函數存在
for kw in ['_showSubjectDetail', '_earningsSessions', 'onclick.*_showSubjectDetail']:
    found = bool(re.search(kw, html))
    print(f"  {'✅' if found else '❌'} '{kw}' in html: {found}")

# 找 onclick 的實際內容
m = re.search(r'onclick="([^"]*_showSubjectDetail[^"]*)"', html)
if m:
    print(f"\nonclick 實際內容: {m.group(1)[:200]}")
else:
    # 可能用單引號
    m2 = re.search(r"onclick='([^']*_showSubjectDetail[^']*)'", html)
    if m2:
        print(f"\nonclick (單引號): {m2.group(1)[:200]}")
    else:
        print("\n❌ 找不到 onclick _showSubjectDetail！")
        # 找 _showSubjectDetail 附近的原始碼
        idx = html.find('_showSubjectDetail')
        if idx >= 0:
            print(f"  位置 {idx}: ...{html[max(0,idx-50):idx+150]}...")
