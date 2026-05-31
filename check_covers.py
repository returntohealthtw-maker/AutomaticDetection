import urllib.request, ssl
ctx = ssl._create_unverified_context()
base = 'https://backend-production-2da61.up.railway.app'
for path in ['/cover.jpg', '/backcover.jpg', '/report-app/cover.jpg', '/report-app/backcover.jpg']:
    url = base + path
    try:
        req = urllib.request.Request(url, method='HEAD')
        r = urllib.request.urlopen(req, context=ctx, timeout=5)
        size = r.headers.get('Content-Length', '?')
        print(path + ': ' + str(r.status) + ' (' + str(size) + ' bytes)')
    except Exception as e:
        print(path + ': ' + str(e))
