import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find CSS text-related layout
patterns = [
    'font-size',
    'line-height',
    'leading',
    'text-content',
    'prose',
    'body-text',
    'section-text',
    'fontSize:"',
    'lineHeight:"',
    'fontSize:',
    'lineHeight:',
]

print("=== Layout CSS patterns ===")
for pat in patterns:
    positions = [m.start() for m in re.finditer(re.escape(pat), js)]
    for p in positions[:2]:
        ctx = js[max(0,p-30):p+80]
        print(f"  [{pat}] → {repr(ctx)}")
    if positions:
        print()

# Look for section/page rendering component
# find "section" with text rendering
idx = js.find('"section-content"')
if idx >= 0:
    print(f"'section-content' at {idx}:")
    print(repr(js[idx:idx+200]))

# Try page width
for pat in ['794', '595', 'A4', '1190', '210mm', '297mm']:
    idx = js.find(pat)
    if idx >= 0:
        ctx = js[max(0,idx-40):idx+80]
        if any(c in ctx for c in ['width', 'height', 'page', 'size', 'px', 'mm', 'pt']):
            print(f"  [{pat}] → {repr(ctx)}")
