import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Confirm current L= assignment context
import re
# find L=9999,y= pattern
idx = js.find('L=9999,y=')
print("=== Current L= context ===")
print(repr(js[idx-100:idx+100]))
print()

# Also check where ym() is called with X
idx2 = js.find('const X=!k&&')
print("=== X computation (display limit) ===")
print(repr(js[idx2:idx2+150]))
print()

# Check prompt word count targets
# Look for 780 and 1600 word count requirements
for pattern in ['780', '1600', '1200', '950']:
    positions = [m.start() for m in re.finditer(pattern, js)]
    print(f"Pattern '{pattern}' found at {len(positions)} locations")
    if positions:
        # Show first few contexts
        for p in positions[:3]:
            ctx = js[p-30:p+60]
            if '字' in ctx or 'char' in ctx.lower() or 'y=' in ctx or 'y =' in ctx:
                print(f"  → {repr(ctx)}")
