import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
t = open('static-app/report-app/assets/index-CqHWGLJp.js', encoding='utf-8').read()

import re
# Find Ox function and Rx map
for m in re.finditer(r'function Ox\(', t):
    print(f'Ox at {m.start()}:')
    print(t[m.start():m.start()+400])
    print()

# Find Rx = {...}
for m in re.finditer(r'\bRx\s*=\s*\{', t):
    print(f'Rx map at {m.start()}:')
    print(t[m.start():m.start()+400])
    print()
