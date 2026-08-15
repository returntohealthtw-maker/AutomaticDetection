import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

i = 1626683
s = max(0, i - 100)
e = min(len(c), i + 4000)
with io.open(r"D:\Write program\AutomaticDetection\tmp_teen_auto_out3.txt", "w", encoding="utf-8") as f:
    f.write(c[s:e])
print("done")
