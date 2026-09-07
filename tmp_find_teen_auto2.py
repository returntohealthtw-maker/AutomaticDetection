import io, re

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

out = []
seen = set()
for t in ['get("auto")', "auto=1", "'auto'"]:
    for m in re.finditer(re.escape(t), c):
        i = m.start()
        if any(abs(i-s) < 30 for s in seen):
            continue
        seen.add(i)
        s = max(0, i - 200)
        e = min(len(c), i + 400)
        out.append(f"=== {t} @ {i} ===\n{c[s:e]}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_teen_auto_out2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done", len(out))
