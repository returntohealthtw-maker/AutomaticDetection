import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

targets = ["兒童腦波分析", "專屬成長報告", "CHILDREN", "NEURAL", "GROWTH REPORT", "SPECTRUM", "RAINBOW BRAIN"]
for t in targets:
    i = c.find(t)
    print(f"=== {t} -> index {i} ===")
    if i >= 0:
        s = max(0, i - 200)
        e = min(len(c), i + 200)
        print(c[s:e])
    print()
