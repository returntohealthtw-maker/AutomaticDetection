import sys, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sessions = [
  {'id':52,'name':'鄭小怡', 'att':55,'med':33,'delta':86,'theta':77,'la':67,'ha':67,'lb':67,'hb':72,'lg':71,'hg':68,'sc':179},
  {'id':51,'name':'鄭小怡', 'att':48,'med':43,'delta':84,'theta':76,'la':65,'ha':65,'lb':66,'hb':69,'lg':68,'hg':66,'sc':175},
  {'id':50,'name':'鄭小怡', 'att':52,'med':55,'delta':82,'theta':74,'la':65,'ha':64,'lb':65,'hb':68,'lg':66,'hg':63,'sc':179},
  {'id':49,'name':'王筱琪', 'att':62,'med':53,'delta':83,'theta':79,'la':69,'ha':66,'lb':66,'hb':72,'lg':70,'hg':65,'sc':179},
  {'id':48,'name':'紀羽珊', 'att':43,'med':56,'delta':89,'theta':79,'la':69,'ha':69,'lb':67,'hb':65,'lg':59,'hg':55,'sc':179},
  {'id':47,'name':'張佩渝', 'att':52,'med':59,'delta':87,'theta':77,'la':67,'ha':65,'lb':65,'hb':63,'lg':57,'hg':55,'sc':179},
  {'id':46,'name':'翁嫣黛', 'att':48,'med':55,'delta':93,'theta':82,'la':71,'ha':71,'lb':70,'hb':69,'lg':67,'hg':64,'sc':179},
  {'id':45,'name':'王筱琪', 'att':0, 'med':0, 'delta':95,'theta':84,'la':71,'ha':70,'lb':69,'hb':72,'lg':71,'hg':66,'sc':179},
  {'id':44,'name':'王筱琪', 'att':5, 'med':2, 'delta':88,'theta':77,'la':67,'ha':66,'lb':67,'hb':67,'lg':63,'hg':58,'sc':129},
  {'id':43,'name':'劉素惠', 'att':60,'med':54,'delta':80,'theta':74,'la':66,'ha':65,'lb':66,'hb':72,'lg':71,'hg':69,'sc':179},
  {'id':42,'name':'劉素惠', 'att':63,'med':41,'delta':79,'theta':73,'la':64,'ha':65,'lb':66,'hb':72,'lg':72,'hg':68,'sc':179},
  {'id':41,'name':'王筱琪', 'att':0, 'med':0, 'delta':96,'theta':85,'la':73,'ha':70,'lb':70,'hb':70,'lg':70,'hg':64,'sc':176},
  {'id':40,'name':'邱心又', 'att':35,'med':52,'delta':92,'theta':80,'la':69,'ha':67,'lb':67,'hb':66,'lg':63,'hg':60,'sc':180},
  {'id':39,'name':'陳暐昕', 'att':69,'med':56,'delta':31,'theta':55,'la':61,'ha':61,'lb':58,'hb':58,'lg':22,'hg':22,'sc':180},
  {'id':38,'name':'鄭小靜', 'att':52,'med':35,'delta':94,'theta':85,'la':73,'ha':73,'lb':73,'hb':73,'lg':73,'hg':73,'sc':180},
  {'id':37,'name':'鄭怡怡', 'att':46,'med':71,'delta':90,'theta':83,'la':71,'ha':71,'lb':71,'hb':71,'lg':70,'hg':70,'sc':180},
  {'id':36,'name':'鄭小怡', 'att':65,'med':32,'delta':77,'theta':72,'la':65,'ha':65,'lb':67,'hb':67,'lg':66,'hg':66,'sc':179},
  {'id':35,'name':'趙亞倫', 'att':60,'med':63,'delta':65,'theta':67,'la':61,'ha':61,'lb':62,'hb':62,'lg':60,'hg':60,'sc':178},
  {'id':34,'name':'趙亞倫', 'att':51,'med':36,'delta':72,'theta':70,'la':62,'ha':62,'lb':62,'hb':62,'lg':60,'hg':60,'sc':79},
  {'id':33,'name':'辜純純', 'att':73,'med':62,'delta':82,'theta':75,'la':66,'ha':66,'lb':67,'hb':67,'lg':63,'hg':63,'sc':179},
]

normal  = [s for s in sessions if s['delta'] < 50]
abnormal= [s for s in sessions if s['delta'] >= 50]

print(f"正常 (Delta<50): {len(normal)} 筆")
print(f"異常 (Delta>=50): {len(abnormal)} 筆")
print()
print("=== 正常 ===")
for s in normal:
    print(f"  #{s['id']} {s['name']}: delta={s['delta']} theta={s['theta']} att={s['att']} lg={s['lg']} hg={s['hg']}")

print()
print("=== 異常特徵 ===")
for s in abnormal:
    all_bands = [s['delta'],s['theta'],s['la'],s['ha'],s['lb'],s['hb'],s['lg'],s['hg']]
    spread = max(all_bands) - min(all_bands)
    all_same = len(set(all_bands)) == 1
    flag = ""
    if s['att']==0 and s['med']==0: flag += " [att/med=ZERO]"
    if all_same: flag += " [所有頻帶完全相同!]"
    if spread < 5: flag += f" [頻帶極度壓縮 spread={spread}]"
    print(f"  #{s['id']} {s['name']:6s}: delta={s['delta']:3d} spread={spread:3d} att={s['att']:3d} hg={s['hg']:3d}{flag}")

print()
print("=== 與陳暐昕(正常)比較 ===")
ref = next(s for s in sessions if s['id']==39)
print(f"參考 #{ref['id']} {ref['name']}: delta={ref['delta']} theta={ref['theta']} la={ref['la']} hg={ref['hg']} lg={ref['lg']}")
print()
for s in abnormal[:8]:
    print(f"#{s['id']} {s['name']:6s}: delta+{s['delta']-ref['delta']:+3d} | theta+{s['theta']-ref['theta']:+3d} | la+{s['la']-ref['la']:+3d} | hg+{s['hg']-ref['hg']:+3d} | lg+{s['lg']-ref['lg']:+3d}")

print()
print("=== 關鍵數字：各 session 的頻帶值範圍 ===")
print(f"{'#':>4} {'name':8s} {'delta':>5} {'theta':>5} {'la':>4} {'ha':>4} {'lb':>4} {'hb':>4} {'lg':>4} {'hg':>4} {'spread':>7} {'判斷':>6}")
for s in sessions:
    bands = [s['delta'],s['theta'],s['la'],s['ha'],s['lb'],s['hb'],s['lg'],s['hg']]
    spread = max(bands) - min(bands)
    ok = "正常" if s['delta'] < 50 else ("無訊號" if s['att']==0 and s['med']==0 else "異常")
    print(f"#{s['id']:>3} {s['name']:8s} {s['delta']:5d} {s['theta']:5d} {s['la']:4d} {s['ha']:4d} {s['lb']:4d} {s['hb']:4d} {s['lg']:4d} {s['hg']:4d} {spread:7d} {ok}")
