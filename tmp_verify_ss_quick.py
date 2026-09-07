import requests, urllib3, random, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
ver = requests.get(BASE + '/app/version', verify=False, timeout=10).json()
print('version=', ver.get('html_version'))
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
h = {'Authorization': 'Bearer '+r.json().get('token','')}
n = 30
random.seed(1)
raw = {k: [] for k in ['attn','medi','r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']}
for i in range(n):
    raw['attn'].append(50); raw['medi'].append(55)
    raw['r_delta'].append(150000); raw['r_theta'].append(60000)
    raw['r_lalpha'].append(15000); raw['r_halpha'].append(12000)
    raw['r_lbeta'].append(8000); raw['r_hbeta'].append(7000)
    raw['r_lgamma'].append(4000); raw['r_hgamma'].append(3000)
p = {
    'subject_name': '_e2e_ss',
    'subject_birthday': '1990-01-01',
    'subject_gender': 'F',
    'subject_age': 36,
    'report_type': 'life_script',
    'sample_count': n,
    'attention_percentage': 50,
    'meditation_percentage': 55,
    'bands_avg': {'delta':40,'theta':30,'low_alpha':20,'high_alpha':18,'low_beta':15,'high_beta':12,'low_gamma':10,'high_gamma':8},
    'raw_arrays': raw,
}
resp = requests.post(BASE+'/eeg/save-stats', headers=h, json=p, verify=False, timeout=90)
print('save-stats HTTP', resp.status_code)
print(resp.text[:500])
if resp.status_code == 200:
    sid = resp.json().get('session_id')
    sl = requests.get(BASE+'/eeg/sessions?limit=10', headers=h, verify=False, timeout=15).json()
    found = [s for s in sl.get('sessions',[]) if s.get('session_id')==sid]
    print('found in list:', bool(found), 'captures=', found[0].get('total_captures') if found else None)
