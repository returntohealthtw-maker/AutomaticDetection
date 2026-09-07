import io, re

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

targets = ["neural", "growth report", "children", "rainbow brain", "spectrum"]
out = []
for t in targets:
    for m in re.finditer(re.escape(t), c, re.IGNORECASE):
        i = m.start()
        s = max(0, i - 250)
        e = min(len(c), i + 250)
        out.append(f"=== {t} @ {i} ===\n{c[s:e]}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_teen_brand_out2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done", len(out))
