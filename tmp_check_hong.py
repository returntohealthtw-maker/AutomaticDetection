import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

sr = requests.get(BASE+'/reports/all-subjects-overview?limit=100&offset=0', headers=h, verify=False)
d = sr.json()
subjects = d if isinstance(d, list) else d.get('subjects') or d.get('data') or []
print("Total subjects:", len(subjects))
for subj in subjects:
    name = subj.get('name') or subj.get('subject_name', '')
    if '洪' in name or '任佑' in name:
        bw = subj.get('latest_brainwave') or {}
        ba = bw.get('bands_avg') or {}
        print("名字:", name)
        print("  Delta=", ba.get('delta'), "Theta=", ba.get('theta'))
        print("  High_a=", ba.get('high_alpha'), "Low_a=", ba.get('low_alpha'))
        print("  High_b=", ba.get('high_beta'), "Low_b=", ba.get('low_beta'))
        print("  High_g=", ba.get('high_gamma'), "Low_g=", ba.get('low_gamma'))
        print("  Source=", bw.get('_source'))
