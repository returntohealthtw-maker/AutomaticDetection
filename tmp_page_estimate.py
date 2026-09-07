import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Find page layout clues: font size, line height, page dimensions
import re
# Search for CSS/style values that define page layout
for pat in ['pageHeight', 'lineHeight', 'fontSize', 'page_height', 'line_height',
            'pageWidth', 'A4', 'marginTop', 'margin-top']:
    idx = js.find(pat)
    if idx >= 0:
        print(f"'{pat}' at {idx}:")
        print(repr(js[idx:idx+120]))
        print()

# Find text rendering / chunk size info
for pat in ['charsPerPage', 'CHARS', 'PAGE_', 'maxChars', 'textLimit']:
    idx = js.find(pat)
    if idx >= 0:
        print(f"'{pat}' at {idx}:")
        print(repr(js[idx:idx+80]))
        print()

# Also look for the ym() function fully
idx = js.find('function ym(')
print("=== ym() full function ===")
print(repr(js[idx:idx+500]))
