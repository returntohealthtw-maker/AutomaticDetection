import io

path = r"D:\Write program\AutomaticDetection\後端系統\static-app\teen-report-app\assets\index-DyIaWXaE.js"
with io.open(path, "r", encoding="utf-8") as f:
    c = f.read()

i = c.find("Ir=async(Nt,bt)=>{const It=await tr(")
s = max(0, i-50)
e = min(len(c), i+3000)
with io.open(r"D:\Write program\AutomaticDetection\tmp_Ir_func_out.txt", "w", encoding="utf-8") as f:
    f.write(c[s:e])
print("done", i)
