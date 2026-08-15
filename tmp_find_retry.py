import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find retry message filter for missing items
search = 'filter(r=>!(G||"").includes('
idx = content.find(search)
print('=== retry message filter ===')
print(f'Found at: {idx}')
print(repr(content[idx:idx+200]))
print()

# Find the full q6 filter section
search2 = 'const q6=['
idx2 = content.find(search2)
print('=== q6 fallback full ===')
print(repr(content[idx2:idx2+300]))
print()

# Show where x is defined (to confirm scope)
search3 = 'const x=c==="1-1"'
idx3 = content.find(search3)
print('=== x variable ===')
print(repr(content[idx3:idx3+100]))
print()

# Find the exact retry loop
search4 = 'let G="";for(let D=0;D<3;D++)'
idx4 = content.find(search4)
print('=== retry loop ===')
print(repr(content[idx4:idx4+100]))
print()

# Check L assignment
search5 = '9999:1050'
idx5 = content.find(search5)
print('=== L=9999:1050 ===')
print(f'Found at: {idx5}')
print(repr(content[idx5-50:idx5+50]))
