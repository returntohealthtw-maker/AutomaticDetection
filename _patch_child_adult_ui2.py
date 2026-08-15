"""
加入「成人（18+）」UI 按鈕（精確版）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# teen 按鈕從 1693360 開始，找其文字內容和結束
# 找到 "約 3～12 歲" 或類似 child button age
idx_child_age = js.find('"約 3～12 歲"')
if idx_child_age < 0:
    idx_child_age = js.find('"約 3~12 歲"')
print(f"Child age text at {idx_child_age}: {repr(js[idx_child_age:idx_child_age+100])}")

# 找 teen 按鈕的年齡文字（往後找）
if idx_child_age > 0:
    idx_teen_age = js.find('"約', idx_child_age + 10)
    print(f"Teen age text at {idx_teen_age}: {repr(js[idx_teen_age:idx_teen_age+100])}")
    
    # 從 teen age 文字後找 teen 按鈕的結束 ]})
    # 應該是 span children 後 }) 關閉 span，再 ]) 關閉 button children array，再 }) 關閉 button
    idx_after_teen_age = idx_teen_age + 30
    # 找 3 個連續的 }) 或 ]})
    area = js[idx_after_teen_age:idx_after_teen_age+200]
    print(f"\nArea after teen age: {repr(area)}")

# 更好的方法：找到 teen 按鈕結束的具體字串
# teen 按鈕裡有 "約 13～18 歲" 這樣的文字
idx_teen_age2 = js.find('"約 13～18 歲"')
if idx_teen_age2 < 0:
    idx_teen_age2 = js.find('"約 13~18 歲"')
if idx_teen_age2 < 0:
    # 找 "13 歲" 相關
    idx_teen_age2 = js.find('"13 歲"')
print(f"\nTeen specific age marker at {idx_teen_age2}")

# 看看 teen 按鈕的 span children 的文字
idx_teen_start = js.find('onClick:()=>G("teen")')
# 從 teen 開始找到後面的 'children:' 包含年齡的字串
area_teen = js[idx_teen_start:idx_teen_start+1000]
print(f"\nTeen button area (first 1000 chars): {repr(area_teen)}")
