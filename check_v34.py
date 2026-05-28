import urllib.request, json, ssl, sys, re
ctx = ssl._create_unverified_context()

req = urllib.request.Request('https://backend-production-2da61.up.railway.app/report-app/index.html')
html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode()
m = re.search(r'src="(/report-app/assets/index-[^"]+\.js)"', html)
js_path = m.group(1) if m else ''
print('JS:', js_path)

if js_path:
    req3 = urllib.request.Request('https://backend-production-2da61.up.railway.app' + js_path)
    js = urllib.request.urlopen(req3, context=ctx, timeout=15).read().decode('utf-8', errors='replace')
    found = 'effectiveData' in js
    print('v34 fix in JS:', found)

# Login and check report 32
data = json.dumps({'phone':'0900000000','password':'admin123'}).encode()
req2 = urllib.request.Request('https://backend-production-2da61.up.railway.app/api/v1/auth/login', data=data, headers={'Content-Type':'application/json'}, method='POST')
token = json.loads(urllib.request.urlopen(req2, context=ctx, timeout=15).read())['token']
req4 = urllib.request.Request('https://backend-production-2da61.up.railway.app/api/v1/reports/list', headers={'Authorization':'Bearer '+token})
reps = json.loads(urllib.request.urlopen(req4, context=ctx, timeout=10).read())
for r in reps.get('reports',[]):
    if r.get('report_id') == 32:
        print('Report#32 status=', r.get('status'))
        pdf = r.get('pdf_url','')
        print('pdf_url:', pdf[:80] if pdf else 'None')
        break
