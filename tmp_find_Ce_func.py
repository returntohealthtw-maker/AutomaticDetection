import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

i = c.find("我的大腦地圖")
s = max(0, i-800)
e = min(len(c), i+100)
print(c[s:e])
