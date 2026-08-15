import io, re

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

out = []
for t in ["我的大腦地圖", "兒童腦波分析", "專屬成長報告", "兒童腦波工作站", "兒童魔法", "青少年五維升級", "青少年腦波"]:
    idxs = [m.start() for m in re.finditer(re.escape(t), c)]
    out.append(f"=== {t}: {len(idxs)} occurrences at {idxs}\n")

with io.open(r"D:\Write program\AutomaticDetection\tmp_cover_text_counts.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")
