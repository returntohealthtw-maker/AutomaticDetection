import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

t = open('static-app/report-app/assets/index-CqHWGLJp.js', encoding='utf-8').read()

checks = [
    ('_chk5da strict check', 'return(nx<0?a.length:nx)-s>=80'),
    ('L=9999 for 1-2', 'L=k||c==="1-2"?9999:1050'),
]
for name, pattern in checks:
    idx = t.find(pattern)
    print(f'{name}: {"OK at "+str(idx) if idx>=0 else "MISSING"}')
    if idx >= 0:
        print(f'  Context: {t[max(0,idx-40):idx+80]}')
    print()
