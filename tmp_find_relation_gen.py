import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()

# Find _generateRelationReport or submitRelationReport
for fn in ['_generateRelationReport', 'submitRelationReport', '_submitRelation', 'generateRelation']:
    idx = content.find(f'function {fn}')
    if idx < 0:
        idx = content.find(f'async function {fn}')
    if idx >= 0:
        ln = content[:idx].count('\n') + 1
        print(f'{fn} at line {ln}:')
        end = content.find('\nasync function ', idx + 50)
        end2 = content.find('\nfunction ', idx + 50)
        end = min(e for e in [end, end2] if e > 0)
        print(content[idx:min(idx+3000, end)])
        print('---')
        break
