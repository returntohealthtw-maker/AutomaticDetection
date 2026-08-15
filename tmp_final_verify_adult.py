import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

checks = [
    ('Av object', 'const Av='),
    ('Ad object', 'const Ad=['),
    ('$u adult_child', 'xinReportType==="adult_child")return Ad'),
    ('ip prompt Av', 'd==="adult_child"?Av[c]'),
    ('ip role adult', '高階成人心理分析師'),
    ('age>=18 G(adult)', 'if(_a>=18)G("adult")'),
    ('Le adult_child', 'ne==="adult"?{...se,xinReportType:"adult_child"}'),
    ('grid-cols-3', 'sm:grid-cols-3'),
    ('adult button onClick', 'onClick:()=>G("adult")'),
    ('adult 18歲', '"18 歲以上"'),
    ('adult amber color', '#d97706'),
]
all_ok = True
for name, marker in checks:
    found = marker in js
    print(f"  {'✓' if found else '✗'} {name}")
    if not found:
        all_ok = False

print(f"\n{'ALL GOOD' if all_ok else 'ISSUES FOUND'}")
