"""
加入「成人（18+）」UI 按鈕到親子報告的 child/teen 選擇器
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# 找到 teen 按鈕的完整結構
# 策略：找 grid 容器，把 grid-cols-2 改成 grid-cols-3，再在 teen 按鈕後加成人按鈕

# 找 teen 按鈕的 onClick 附近
idx_teen = js.find('onClick:()=>G("teen")')
print(f"Teen btn onClick at {idx_teen}")

# 看看 teen 按鈕是怎麼結束的
teen_area = js[idx_teen:idx_teen+800]
print(f"Teen btn area: {repr(teen_area[:400])}")

# 找到 teen 按鈕塊的結束（找 ]})] 或 })）
# 策略：找到 teen 按鈕後的特定標記來定位插入點
# 在 teen 按鈕後找 "]}）" 再插入 adult 按鈕

# 找到 teen 按鈕 title text 特定字串
teen_title_marker = 'children:["🧑‍🎓'
if teen_title_marker not in js:
    teen_title_marker = 'children:["🎓'
    if teen_title_marker not in js:
        # 找 teen 按鈕的 children 文字
        idx_teen_ch = js.find('"青少年"', idx_teen)
        if idx_teen_ch < 0:
            idx_teen_ch = js.find('"13-18歲"', idx_teen)
        print(f"Teen title children at {idx_teen_ch}: {repr(js[idx_teen_ch:idx_teen_ch+100]) if idx_teen_ch>0 else 'not found'}")

# 直接搜索 teen 按鈕後的結構
# 找 "children" text 在 teen button 中
print("\n=== Looking for teen button text content ===")
idx_t2 = js.find('"13～18', idx_teen)
if idx_t2 < 0:
    idx_t2 = js.find('"13~18', idx_teen)
if idx_t2 < 0:
    idx_t2 = js.find('"青少年"', idx_teen)
print(f"teen text at {idx_t2}: {repr(js[idx_t2:idx_t2+200]) if idx_t2>0 else 'not found'}")

# 找 teen 按鈕組件的結束
# 從 onClick:()=>G("teen") 開始，找到這個 button 的 })] 結束
# teen button 應該在 } 之後接 )] 結束 children array
idx_teen_end = js.find('])', idx_teen + 500)
print(f"\nTeen button children end at {idx_teen_end}: {repr(js[idx_teen_end-50:idx_teen_end+50])}")

# 嘗試找到 grid 容器
idx_grid = js.rfind('grid grid-cols-1 sm:grid-cols-2', 0, idx_teen + 10)
print(f"\nGrid cols-2 at {idx_grid}: {repr(js[idx_grid:idx_grid+200])}")

# 把 grid-cols-2 改成 grid-cols-3
if idx_grid > 0:
    old_grid = '"grid grid-cols-1 sm:grid-cols-2"'
    new_grid = '"grid grid-cols-1 sm:grid-cols-3"'
    if old_grid in js[idx_grid:idx_grid+100]:
        # 找到準確位置
        actual_idx = js.find(old_grid, idx_grid)
        print(f"Grid actual at {actual_idx}")
    
print("\n=== Full grid container area ===")
print(repr(js[idx_grid:idx_grid+1200]))
