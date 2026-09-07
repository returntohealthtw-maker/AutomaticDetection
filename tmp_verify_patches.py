import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    # Patch 6: L=9999 globally
    ('L=9999', 'PASS: L=9999 applied'),
    ('L=k||c==="1-2"?9999:1050', 'FAIL: Old L=1050 still present'),
    # Patch 7: q6 filter with 80-char check
    ('const q6=["一","二","三","四","五"].filter((D,i,ar)=>{', 'PASS: q6 80-char filter applied'),
    ('const q6=["一","二","三","四","五"].filter(D=>!G.includes', 'FAIL: Old q6 filter still present'),
    # Patch 8: retry message with 80-char check
    ('filter((r,i,ar)=>{', 'PASS: retry message 80-char filter applied'),
    ('filter(r=>!(G||"").includes', 'FAIL: Old retry filter still present'),
    # Patch 9: 5 retries for x sections
    ('for(let D=0;D<(x?5:3);D++)', 'PASS: retry count increased to 5 for x'),
    ('for(let D=0;D<3;D++)', 'FAIL: Old D<3 retry loop still present'),
    # _chk5da still intact
    ('return(nx<0?a.length:nx)-s>=80})', 'PASS: _chk5da 80-char check intact'),
]

for pattern, msg in checks:
    found = pattern in content
    if 'PASS' in msg:
        status = 'PASS' if found else 'MISSING'
    else:
        status = 'FAIL' if found else 'OK'
    print(f'[{status}] {msg[:70]}')
