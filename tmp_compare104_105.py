import sys, os, requests, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '後端系統'))
from app.services.braindna_algorithms import compute_all

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
h = {'Authorization': f'Bearer {token}'}

SCREENSHOT = {
    104: dict(delta=58, theta=76, low_alpha=63, high_alpha=100, low_beta=66, high_beta=70, low_gamma=62, high_gamma=70),
    105: dict(delta=58, theta=58, low_alpha=56, high_alpha=48,  low_beta=52, high_beta=73, low_gamma=74, high_gamma=76),
}
KEY_MAP = {'delta':'r_delta','theta':'r_theta','low_alpha':'r_lalpha','high_alpha':'r_halpha',
           'low_beta':'r_lbeta','high_beta':'r_hbeta','low_gamma':'r_lgamma','high_gamma':'r_hgamma'}

for sid in [104, 105]:
    caps_raw = requests.get(f'{base}/sessions/{sid}/captures', headers=h).json()
    captures = caps_raw if isinstance(caps_raw, list) else caps_raw.get('captures', [])
    raw = {rk: [c.get(dk, 0) for c in captures] for dk, rk in KEY_MAP.items()}
    result = compute_all(raw, is_child=False)
    bdna = result.get('bands', {})
    sc = SCREENSHOT[sid]

    print(f"Session #{sid}  N={len(captures)}  scale={result.get('input_scale')}")
    print(f"{'Band':<12} {'截圖':>5} {'後端':>5} {'差':>4}")
    print('-' * 32)
    all_ok = True
    for dk in ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']:
        sv = sc[dk]
        bv = round(bdna.get(dk, 0))
        diff = bv - sv
        mark = 'OK' if abs(diff) <= 2 else f'差{diff:+d}'
        if abs(diff) > 2:
            all_ok = False
        print(f"  {dk:<12} {sv:>5} {bv:>5} {str(diff):>4}  {mark}")
    print(f"=> {'全部吻合!' if all_ok else '有差異，見上方'}")
    print()
