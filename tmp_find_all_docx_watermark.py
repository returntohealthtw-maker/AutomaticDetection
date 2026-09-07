import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

for i in [1643179, 1646494, 1646897, 1654609]:
    s = max(0, i-150)
    e = min(len(c), i+150)
    print(f"=== @ {i} ===")
    print(c[s:e])
    print()
