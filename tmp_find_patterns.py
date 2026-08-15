import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find l6() function
idx = content.find('function l6(')
print('=== l6 function ===')
print(content[idx:idx+400])
print()

# Find q6 fallback
idx2 = content.find('const q6=[')
print('=== q6 fallback ===')
print(content[idx2:idx2+400])
print()

# Find retry loop
marker = 'let G="";for(let D=0'
idx3 = content.find(marker)
print('=== retry loop ===')
print(content[idx3:idx3+150])
print()

# Find L=k assignment context
marker2 = '9999:1050'
idx4 = content.find(marker2)
print('=== L assignment ===')
print(content[idx4-200:idx4+300])
print()

# Find X= line near ym(G,
marker3 = 'const X=!k&&'
idx5 = content.find(marker3)
print('=== X computation ===')
print(content[idx5:idx5+200])
