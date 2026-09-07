import re
p = open('後端系統/static-app/report-app/assets/index-CqHWGLJp.js', encoding='utf-8').read()
ws_idx = p.find('const Ws=[')
ws_chunk = p[ws_idx:ws_idx+3000]
subs = re.findall(r'subs:\[([^\]]+)\]', ws_chunk)
total = sum(len(re.findall(r'"[0-9]+-[0-9]+\.', s)) for s in subs)
print(f'Total chapters: {len(subs)}, Total subsections: {total}')
print(f'Each subsection = 1 Gemini text call (up to 5 retries) + 1 Imagen call')
print(f'Worst case: {total} x 5 retries x 120s = {total*5*120//60} minutes')
print(f'Average case: {total} x 1.5 retries x 20s = {total*1*20//60} minutes')
print()
print('Sections with 5-retry + patch logic (1-1, 1-3):')
print('  2 sections x 6 calls x 120s = ', 2*6*120//60, 'minutes worst case')
