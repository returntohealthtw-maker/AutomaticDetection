"""
_patch_child_report_js.py — MBTI v6.0 + 第2章重新設計（兒童報告）

Patch C1: bw() MBTI 計算改用 v6.0 直接競爭演算法
Patch C2: ac 第2章小節標題更新
Patch C3: dw["2-1"] ~ dw["2-4"] prompts 重設計（兒童版：性格矛盾、情緒地雷、修復路徑）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
BKUP    = JS_PATH + '.bakC'

with open(JS_PATH, 'r', encoding='utf-8') as f:
    js = f.read()

# Save backup
with open(BKUP, 'w', encoding='utf-8') as f:
    f.write(js)
print(f"Backup saved: {BKUP}")

patches_ok = []
patches_fail = []

def apply_patch(name, old, new):
    global js
    if old not in js:
        patches_fail.append(name)
        print(f"  [FAIL] {name}: old string not found")
        return False
    count = js.count(old)
    if count > 1:
        print(f"  [WARN] {name}: found {count} occurrences, replacing first only")
    js = js.replace(old, new, 1)
    patches_ok.append(name)
    print(f"  [OK]   {name}")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# PATCH C1 — bw() 改用 v6.0 直接競爭算法（兒童報告）
# ─────────────────────────────────────────────────────────────────────────────
OLD_BW = (
    'function bw(a,t=!1){'
    'const e=x6(a),i=t?k6(a.lowAlpha,a.theta):A6(a.lowAlpha),'
    's=N6(i,a.theta),l=T6(s,a.lowAlpha,a.theta);'
    'return{mindColor:e,mindColorId:Number(e),mindColorName:v6[e],'
    'mindColorEn:w6[e],bagua:i,baguaName:_6[i],'
    'mbti:s,mbtiEn:P5[s].en,mbtiZh:P5[s].zh,'
    'EI:l.EI,NS:l.NS,TF:l.TF,JP:l.JP}}'
)

NEW_BW = (
    'function bw(a,t=!1){'
    'const e=x6(a),i=t?k6(a.lowAlpha,a.theta):A6(a.lowAlpha);'
    # v6.0 IIFE — 兒童報告和成人完全相同的算法核心
    'const _v6=(function(d){'
    'var Ea=d.focus*.35+d.highGamma*.35+d.highBeta*.30,'
    'Ia=d.highAlpha*.40+d.relaxation*.30+d.lowAlpha*.30,ei=Ea-Ia;'
    'var Na=d.theta*.60+d.highAlpha*.40,Sa=d.lowBeta*.55+d.highGamma*.45,ns=Na-Sa;'
    'var Ta=d.lowBeta*.50+d.highBeta*.50,Fa=d.lowGamma*.55+d.highAlpha*.45,tf=Ta-Fa;'
    'var Ja=d.highBeta*.45+d.focus*.55,Pa=d.theta*.50+d.relaxation*.50,jp=Ja-Pa;'
    "var mt=(ei>0?'E':'I')+(ns>8?'N':'S')+(tf>0?'T':'F')+(jp>0?'J':'P');"
    'var cl=function(v){return Math.max(5,Math.min(99,Math.round(v)))},'
    'cl78=function(v){return Math.max(10,Math.min(78,Math.round(v)))};'
    "var bd=[{ax:'EI',d:Math.abs(ei),p:0,f:ei>0?'I':'E'},"
    "{ax:'NS',d:Math.abs(ns-8),p:1,f:ns>8?'S':'N'},"
    "{ax:'TF',d:Math.abs(tf),p:2,f:tf>0?'F':'T'},"
    "{ax:'JP',d:Math.abs(jp),p:3,f:jp>0?'P':'J'}]"
    '.sort(function(x,y){return x.d-y.d});'
    'var sec=[];'
    'for(var bi=0;bi<Math.min(2,bd.length);bi++){'
    'var st=cl78(78-bd[bi].d*1.8);if(st<20)break;'
    "var tt=mt.split('');tt[bd[bi].p]=bd[bi].f;"
    "sec.push({mbti:tt.join(''),strength:st,axis:bd[bi].ax,"
    "reason:bd[bi].ax+'軸邊界'})}"
    'return{mbti:mt,'
    'EI:cl(50+ei*.6),NS:cl(50+(ns-8)*.6),TF:cl(50+tf*.6),JP:cl(50+jp*.6),'
    'eiDiff:ei,nsDiff:ns,tfDiff:tf,jpDiff:jp,secondaries:sec}'
    '})(a);'
    'return{mindColor:e,mindColorId:Number(e),mindColorName:v6[e],'
    'mindColorEn:w6[e],bagua:i,baguaName:_6[i],'
    'mbti:_v6.mbti,mbtiEn:(P5[_v6.mbti]||{}).en||\'\','
    'mbtiZh:(P5[_v6.mbti]||{}).zh||\'\','
    'EI:_v6.EI,NS:_v6.NS,TF:_v6.TF,JP:_v6.JP,'
    'eiDiff:_v6.eiDiff,nsDiff:_v6.nsDiff,tfDiff:_v6.tfDiff,jpDiff:_v6.jpDiff,'
    'secondaries:_v6.secondaries}}'
)

apply_patch("PatchC1_bw_v6", OLD_BW, NEW_BW)

# ─────────────────────────────────────────────────────────────────────────────
# PATCH C2 — 兒童第2章小節標題更新
# ─────────────────────────────────────────────────────────────────────────────
OLD_CHILD_CH2_TITLE = (
    '{title:"我是什麼性格？",subs:['
    '"2-1. 性格寶石強度","2-2. 大腦怎麼決定我的性格",'
    '"2-3. 我做選擇的方式","2-4. 心情好 vs 心情不好時的我"]}'
)
NEW_CHILD_CH2_TITLE = (
    '{title:"我是什麼性格？",subs:['
    '"2-1. 性格寶石強度（v6.0）","2-2. 大腦怎麼決定我的性格",'
    '"2-3. 我的性格矛盾 × 情緒地雷","2-4. 心情好 vs 心情不好時的我"]}'
)
apply_patch("PatchC2_ch2_titles", OLD_CHILD_CH2_TITLE, NEW_CHILD_CH2_TITLE)

# ─────────────────────────────────────────────────────────────────────────────
# PATCH C3 — 兒童 dw ch2 prompts 重設計
# ─────────────────────────────────────────────────────────────────────────────
OLD_CHILD_DW_START = '"2-1":"【MBTI 腦波演算法】E/I：(γ↑+專注力)÷2 vs (α↓+放鬆度)÷2'
OLD_CHILD_DW_END   = '並提供一個讓自己快速回到最好狀態的小秘訣"'

c_start = js.find(OLD_CHILD_DW_START)
c_end   = js.find(OLD_CHILD_DW_END) + len(OLD_CHILD_DW_END)

if c_start < 0 or c_end <= c_start:
    patches_fail.append("PatchC3_dw_ch2")
    print("  [FAIL] PatchC3_dw_ch2: boundary not found")
else:
    new_child_dw = (
        # 2-1 性格寶石強度 v6.0
        '"2-1":"【性格寶石演算法 v6.0】\n'
        '計算4個性格軸（v6.0直接競爭）：\n'
        '  E/I：(focus×0.35+γ↑×0.35+β↑×0.30) vs (α↑×0.40+放鬆×0.30+α↓×0.30)\n'
        '  N/S：(θ×0.60+α↑×0.40) vs (β↓×0.55+γ↑×0.45)，N需大於S超過8\n'
        '  T/F：(β↓+β↑)/2 vs (γ↓×0.55+α↑×0.45)\n'
        '  J/P：(β↑×0.45+focus×0.55) vs (θ×0.50+放鬆×0.50)\n'
        '次性格：4軸各自距臨界值的距離（最近2個軸翻轉），強度60-78%=日常浮現，40-59%=特定情境\n\n'
        '寶石對應（可選用）：INTJ/INFJ=紫水晶（深思者）、ENTP/ENFP=彩虹石（探索者）、\n'
        '  ISTJ/ISFJ=翡翠（守護者）、ESTJ/ESFJ=黃金（實踐者）、\n'
        '  INTP/ISTP=水晶（分析者）、ENFJ/ENTJ=紅寶石（引領者）\n\n'
        '撰寫：\n'
        '①用寶石比喻說明主性格（語氣像在介紹一顆獨特的寶石，讓孩子驕傲）\n'
        '②描述這顆寶石在學校、家裡、和朋友玩時的三種閃光表現\n'
        '③若有次性格：說明「有時候你也會變成[次性格寶石名]」的觸發情境（用可愛比喻）\n'
        '④最後用一句鼓勵語：「你的性格超級特別，因為...」",'

        # 2-2 大腦怎麼決定我的性格 + 交互作用
        '"2-2":"【v6.0 腦波如何決定性格 × 性格間的合作（兒童版）】\n'
        'v6.0四軸腦波比喻（用小朋友懂的語言）：\n'
        '  EI軸：focus/γ↑/β↑是「外向能量電池」（越高越想找朋友玩、越喜歡熱鬧）\n'
        '        α↑/放鬆/α↓是「內向充電寶」（越高越喜歡安靜獨處充電）\n'
        '  NS軸：θ/α↑是「想像力魔法棒」（越高越愛做白日夢、想很多可能性）\n'
        '        β↓/γ↑是「超厲害的觀察眼鏡」（越高越注意細節、喜歡具體事實）\n'
        '  TF軸：β↓/β↑是「邏輯分析腦袋」（越高越愛用道理說話、分析問題）\n'
        '        γ↓/α↑是「同理心超雷達」（越高越懂別人的感受、在乎大家開不開心）\n'
        '  JP軸：β↑/focus是「計畫小本本」（越高越愛提前安排好、有規律）\n'
        '        θ/放鬆是「彈性橡皮擦」（越高越喜歡隨機應變、靈活有創意）\n\n'
        '撰寫（代入此孩子的具體腦波數值）：\n'
        '①說明孩子4個「腦波特點」的強弱（引用具體數值，語氣像介紹超能力）\n'
        '②找出最強的2個腦波特點，說明它們一起合作時產生什麼有趣能力\n'
        '  例：高θ+高γ↓=既有想像力又懂別人心情，是天生的說故事高手！\n'
        '③說明次性格是怎麼形成的（哪個軸最接近翻轉，在什麼情況下切換）\n'
        '④整段語氣要讓孩子感到「哇，我的大腦好厲害！」",'

        # 2-3 我的性格矛盾 × 情緒地雷
        '"2-3":"【v6.0 性格小矛盾 × 情緒地雷（兒童版）】\n'
        '計算邊界距（代入具體數值）：\n'
        '  EI邊界距=|(focus×0.35+γ↑×0.35+β↑×0.30)-(α↑×0.40+放鬆×0.30+α↓×0.30)|\n'
        '  NS邊界距=|(θ×0.60+α↑×0.40)-(β↓×0.55+γ↑×0.45)-8|\n'
        '  TF邊界距=|(β↓+β↑)/2-(γ↓×0.55+α↑×0.45)|\n'
        '  JP邊界距=|(β↑×0.45+focus×0.55)-(θ×0.50+放鬆×0.50)|\n'
        '  邊界距最小=最強的性格小矛盾\n\n'
        '撰寫（用溫暖幽默的兒童語氣，讓孩子感到「被精準看見」且「這很正常」）：\n'
        '①【性格小矛盾故事】（100字）\n'
        '  用可愛比喻說明孩子心裡最強的矛盾（邊界距最小的1-2個軸）\n'
        '  例：JP軸最小→「一部分的你超愛把所有事情計畫好，另一部分的你卻想隨心所欲」\n'
        '  讓孩子看完後說：「對！就是這樣！」\n\n'
        '②【情緒地雷（2-3個，根據主MBTI型別選取）】（150字）\n'
        '  N型地雷：被說「不要想那麼多、只看眼前就好」時，感到自己的想像力不被重視\n'
        '  S型地雷：沒有明確步驟、要靠直覺做事時，感到迷失不安\n'
        '  T型地雷：大家都靠感情說話不講道理時，感到困惑沮喪\n'
        '  F型地雷：被說「你太敏感了」或情感不被重視時，感到受傷\n'
        '  J型地雷：計畫突然改變，感到世界要崩塌了！\n'
        '  P型地雷：被強迫立刻決定，感到窒息無法思考\n'
        '  E型地雷：一直沒有朋友可以說話，能量快速流失\n'
        '  I型地雷：一直被人圍著沒有安靜的時間，覺得很累\n'
        '  只選符合此孩子主MBTI的2-3個，用溫暖語氣說明並讓孩子知道這很正常\n\n'
        '③ 用一句話告訴孩子：「下次你發現自己心裡有這個矛盾時，代表你的大腦在成長！」",'

        # 2-4 心情好 vs 心情不好時的我
        '"2-4":"【v6.0 穩定態 vs 壓力態性格差異（兒童版）】\n'
        '計算：穩定指數=α↓÷β↑（>1=超穩定，0.7-1=一般，<0.7=比較容易受影響）\n'
        '壓力張力=β↑-α↓；壓力態轉換軸=邊界距最小的軸（與2-3相同）\n\n'
        '撰寫（用天氣比喻：晴天=穩定態，陰雨天=壓力態）：\n\n'
        '①【超晴天的你！（穩定態）】（80字）\n'
        '  當α↓高且放鬆度好時，此MBTI型最閃亮的3個超能力是什麼？\n'
        '  引用具體數值評估孩子目前「晴天比例」，讓孩子感到驕傲\n\n'
        '②【有時候會下雨的你（壓力態）】（120字）\n'
        '  當β↑-α↓>15，或壓力指數<0.7時，這個孩子的哪些特質會「走音」？\n'
        '  v6.0規則：邊界距最小的軸翻轉→出現暫時的「雨天性格」\n'
        '  具體說明：可能變得更任性/更沉默/更愛哭/更容易發脾氣/更猶豫不決\n'
        '  用溫暖語氣：「這不是你變壞了，只是大腦電量有點低！」\n\n'
        '③【2個讓心情快速回到晴天的充電秘訣】（80字）\n'
        '  根據孩子的腦波特點，給出2個具體的「充電方法」：\n'
        '  EI軸偏I→找一個安靜角落15分鐘；EI軸偏E→找朋友說說話10分鐘\n'
        '  高θ→睡前畫畫或寫故事5分鐘；高γ↓→抱抱喜歡的人或寵物\n'
        '  高β↑→跑步/跳繩消耗多餘能量；高γ↑→安靜坐著深呼吸\n'
        '  選2個最符合此孩子腦波的方法，用遊戲化語言讓孩子想立刻去試\n\n'
        '④ 用鼓勵語結尾：「你現在就很棒！每個人都有晴天和雨天，懂得自己的心情訊號，就是最厲害的超能力！」"'
    )

    js = js[:c_start] + new_child_dw + js[c_end:]
    patches_ok.append("PatchC3_dw_ch2")
    print("  [OK]   PatchC3_dw_ch2")

# ─────────────────────────────────────────────────────────────────────────────
# 寫回檔案
# ─────────────────────────────────────────────────────────────────────────────
with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print()
print(f"Done. OK={len(patches_ok)} FAIL={len(patches_fail)}")
if patches_fail:
    print("FAILED:", patches_fail)
else:
    print("All patches applied successfully.")
