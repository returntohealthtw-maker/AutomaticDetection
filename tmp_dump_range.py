import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

s, e = 1653500, 1662500
with io.open(r"D:\Write program\AutomaticDetection\tmp_dump_range_out.txt", "w", encoding="utf-8") as f:
    f.write(c[s:e])
print("done", e-s)
