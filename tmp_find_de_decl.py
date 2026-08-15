import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

i = c.find("[de,ee]")
print("index", i)
s = max(0, i-200)
e = min(len(c), i+200)
print(c[s:e])
