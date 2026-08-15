import io, re

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

out = []
for m in re.finditer("兒童", c):
    i = m.start()
    s = max(0, i - 120)
    e = min(len(c), i + 120)
    out.append(f"=== 兒童 @ {i} ===\n{c[s:e]}\n")

for m in re.finditer(r"\bChild\b", c, re.IGNORECASE):
    i = m.start()
    s = max(0, i - 120)
    e = min(len(c), i + 120)
    out.append(f"=== Child @ {i} ===\n{c[s:e]}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_teen_brand_out4.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done", len(out))
