import io, re

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

out = []
for t in [re.escape("[ie,"), re.escape(",ie]"), re.escape("ie,$a"), re.escape("$a(")]:
    for m in re.finditer(t, c):
        i = m.start()
        s = max(0, i-150)
        e = min(len(c), i+150)
        out.append(f"=== {t} @ {i} ===\n{c[s:e]}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_ie_state_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done", len(out))
