import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 找 z6 定義
idx = js.find('function z6(')
if idx < 0:
    idx = js.find('z6=function(')
if idx < 0:
    # 找 z6( 的第一個出現（可能是箭頭函式）
    idx = js.find(',z6=(')
    if idx < 0:
        idx = js.find('z6=(')
print(f"z6 at {idx}: {repr(js[max(0,idx-20):idx+400])}")

# 找 852522 那段的更大上下文
print("\n=== prompt selection context (852400-852700) ===")
print(repr(js[852400:852700]))

# 找主 prompt 函式名稱
print("\n=== find prompt-generating function ===")
# 852522 前找最近的 function 或 async function
func_idx = js.rfind('async function ', 0, 852522)
print(f"async func before 852522 at {func_idx}: {repr(js[func_idx:func_idx+80])}")
func_idx2 = js.rfind('=>{', 0, 852522)
print(f"arrow func before 852522 at {func_idx2}: {repr(js[max(0,func_idx2-50):func_idx2+80])}")
