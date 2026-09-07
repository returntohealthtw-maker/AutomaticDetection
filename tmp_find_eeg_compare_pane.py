import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()
idx = content.find('admin-pane-eeg-compare')
ln = content[:idx].count('\n') + 1
print(f'admin-pane-eeg-compare at line {ln}')
# Find end of this pane
end = content.find('<!-- ──', idx + 100)
end2 = content.find('</div>\n\n        <!-- ──', idx)
print(f'  end1 at {end}')
print(f'  end2 at {end2}')
# Show from idx to 500 chars
print(content[idx:idx+400])
print('...')
# Find the closing of the screen
sidx = content.rfind('</div>', 0, idx + 3000)
print(f'\nLast </div> before +3000: at char {sidx}')
