import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. ac 完整結構
ac_start = js.find('const ac=[')
ac_end = js.find('];function $u', ac_start)
print(f"=== ac structure [{ac_start}:{ac_end}] ===")
print(js[ac_start:ac_end+1])

print("\n" + "="*60)

# 2. vw 完整 prompts
vw_start = js.find('const vw={')
# 找結束 - 下一個 const 或 };
vw_end = js.find('};function ', vw_start)
if vw_end < 0:
    vw_end = js.find('\nconst ', vw_start)
print(f"\n=== vw prompts [{vw_start}:{vw_end}] ===")
print(js[vw_start:vw_end+2])

print("\n" + "="*60)

# 3. G(setter for ne state) 的呼叫
# 找 auto-generation 時 ne 如何被設定
age_idx = js.find('"age"]=parseInt')
print(f"\n=== age URL param area (1629400-1630000) ===")
print(repr(js[1629400:1630000]))

# 4. ne/G state 附近
ne_state_idx = js.find('[ne,G]=gt.useState("child")')
print(f"\n=== ne state def at {ne_state_idx} (context) ===")
print(repr(js[ne_state_idx:ne_state_idx+500]))
