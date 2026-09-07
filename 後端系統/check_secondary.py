import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
t = open('static-app/report-app/assets/index-CqHWGLJp.js', encoding='utf-8').read()

# Look at secondaries rendering in the 2-1 SVG (around line 238024)
idx = t.find('secondaries:[]}}')
print('Default empty secondaries at:', idx)
print(t[idx:idx+200])
print()

# Look at how 2-1 uses secondaries in the SVG chart
idx2 = t.find('b=r.secondaries')
print('b=r.secondaries at:', idx2)
print(t[idx2:idx2+800])
print()

# How many secondary items are shown
idx3 = t.find('slice(0,3)')
print('slice(0,3) near secondaries:', idx3)
print(t[max(0,idx3-100):idx3+200])
