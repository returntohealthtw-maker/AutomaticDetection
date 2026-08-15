import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

targets = [
    ('h1', 1655959, 200),
    ('h2', 1657896, 260),
]
out = []
for name, i, span in targets:
    s = max(0, i-20)
    e = min(len(c), i+span)
    out.append(f"=== {name} @ {i} ===\n{c[s:e]}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_edit_snippets.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")
