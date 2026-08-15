"""
_patch_report_js4.py — MBTI v6.0 直接競爭演算法 + 第2章重新設計
套用到 index-CqHWGLJp.js（成人報告）

Patch 10: wu() fallback 改用 v6.0 內聯 IIFE 算法
Patch 11: Ws 第2章標題更新
Patch 12: dw["2-1"] ~ dw["2-4"] prompts 全面重設計（性格交互、矛盾、情緒地雷、修復路徑）
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS_PATH  = r'D:\Write program\AutomaticDetection\後端系統\static-app\report-app\assets\index-CqHWGLJp.js'
BKUP     = JS_PATH + '.bak4'

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
# PATCH 10 — wu() fallback 改用 v6.0 IIFE
# ─────────────────────────────────────────────────────────────────────────────
OLD_WU_FALLBACK = (
    'const r=Ux({highAlpha:a.highAlpha,lowAlpha:a.lowAlpha,highBeta:a.highBeta,'
    'lowBeta:a.lowBeta,lowGamma:a.lowGamma,highGamma:a.highGamma,theta:a.theta,'
    'focus:a.focus,relaxation:a.relaxation}),[e,i]=F5[r.mbti]??["未知型",""],'
    'u=(r.secondaries??[]).map(s=>{const[c,l]=F5[s.mbti]??["未知型",""];'
    'return{type:s.mbti,label:c,desc:l,strength:s.strength,reason:s.reason}});'
    'return{type:r.mbti,ei:r.EI-50,ns:r.NS-50,tf:r.TF-50,jp:r.JP-50,'
    'label:e,desc:i,bagua:r.bagua,baguaName:r.baguaName,'
    'mindColorName:r.mindColorName,secondaries:u}'
)

# v6.0 IIFE 內聯：保留 Ux() 取 mindColor/bagua，MBTI 改用 v6.0 直接競爭
NEW_WU_FALLBACK = (
    'const r=Ux({highAlpha:a.highAlpha,lowAlpha:a.lowAlpha,highBeta:a.highBeta,'
    'lowBeta:a.lowBeta,lowGamma:a.lowGamma,highGamma:a.highGamma,theta:a.theta,'
    'focus:a.focus,relaxation:a.relaxation});'
    # v6.0 IIFE
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
    # 用 v6.0 結果建構 return
    'const [e,i]=F5[_v6.mbti]??["未知型",""],'
    'u=(_v6.secondaries??[]).map(s=>{'
    'const[c,l]=F5[s.mbti]??["未知型",""];'
    'return{type:s.mbti,label:c,desc:l,strength:s.strength,reason:s.reason}});'
    'return{type:_v6.mbti,ei:_v6.EI-50,ns:_v6.NS-50,tf:_v6.TF-50,jp:_v6.JP-50,'
    'label:e,desc:i,bagua:r.bagua,baguaName:r.baguaName,'
    'mindColorName:r.mindColorName,secondaries:u,'
    'eiDiff:_v6.eiDiff,nsDiff:_v6.nsDiff,tfDiff:_v6.tfDiff,jpDiff:_v6.jpDiff}'
)

apply_patch("Patch10_wu_v6", OLD_WU_FALLBACK, NEW_WU_FALLBACK)

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 11 — 成人報告第2章標題更新
# ─────────────────────────────────────────────────────────────────────────────
OLD_CH2_TITLE = (
    '"主性格 × 腦波運作",subs:['
    '"2-1. 主性格強度圖","2-2. 腦波如何形成主性格",'
    '"2-3. 主性格的決策模式","2-4. 成熟與壓力狀態的性格差異"]'
)
NEW_CH2_TITLE = (
    '"主性格 × 性格動力學",subs:['
    '"2-1. 主性格 × 四軸強度","2-2. 腦波四軸成因 × 交互作用",'
    '"2-3. 性格矛盾張力 × 情緒地雷","2-4. 壓力態變形 × 修復路徑"]'
)
apply_patch("Patch11_ch2_titles", OLD_CH2_TITLE, NEW_CH2_TITLE)

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 12 — 成人 dw ch2 prompts 全面重設計
# ─────────────────────────────────────────────────────────────────────────────
OLD_DW_CH2_START = '"2-1":`【腦波性格地圖——主性格 × 多元次性格解讀】根據腦波頻率計算此人在MBTI性格地圖上的精確位置'
OLD_DW_CH2_END   = '並給出最關鍵的一個具體成長建議，絕對不可以提到任何易經或玄學'

old_start_idx = js.find(OLD_DW_CH2_START)
old_end_idx   = js.find(OLD_DW_CH2_END) + len(OLD_DW_CH2_END)

if old_start_idx < 0 or old_end_idx <= old_start_idx:
    patches_fail.append("Patch12_dw_ch2")
    print("  [FAIL] Patch12_dw_ch2: boundary not found")
else:
    old_block = js[old_start_idx:old_end_idx]

    new_dw_ch2 = (
        # 2-1 主性格 × 四軸強度
        '"2-1":`【MBTI v6.0 主性格 × 四軸強度解析】\n'
        '已預算完成（請直接使用，不要自行重算）。絕對禁止出現任何易經、八卦、卦象等字眼，只用腦波科學語言。\n\n'
        '第一部分【主性格深度解析】（220字）\n'
        '  以「主性格：[MBTI]（[中文名稱]）」為標題，從v6.0四軸角度說明此型核心特質：\n'
        '  ①決策風格（JP軸>50=執行導向，<50=探索導向）\n'
        '  ②人際模式（EI軸>50=外部激活，<50=內部充電）\n'
        '  ③訊息處理（NS軸>50=直覺跳躍，<50=感知細節）\n'
        '  ④情感取向（TF軸>50=邏輯優先，<50=共情優先）\n'
        '  ——必須引用4個具體軸分數+2-3個腦波原始數值，說明「為何這組腦波讓此人展現此性格」\n\n'
        '第二部分【次性格逐一解析（依強度由高到低）】（每個120字）\n'
        '  格式：「【次性格：[MBTI]（[中文名稱]，邊界強度：XX%）】」\n'
        '  ①此次性格是主性格哪個軸接近翻轉的結果（強度越高=日常越容易浮現）\n'
        '  ②在哪些具體情境下浮現：工作高壓/親密關係/獨處反思/陌生社交\n'
        '  ③此次性格與主性格如何形成資源互補，或製造內在矛盾\n\n'
        '第三部分【四軸確定性總評】（60字）\n'
        '  最確定的軸（分數離50最遠）=此人的性格錨點\n'
        '  最模糊的軸（分數最接近50）=此人的性格彈性來源（也是最常困惑的地方）`,'

        # 2-2 腦波四軸成因 × 交互作用
        '"2-2":"【v6.0 四軸腦波成因 × 性格交互作用分析】\n'
        'v6.0各軸計算公式（請代入具體數值分析）：\n'
        '  E_score=focus×0.35+γ↑×0.35+β↑×0.30；I_score=α↑×0.40+放鬆×0.30+α↓×0.30；eiDiff=E-I\n'
        '  N_score=θ×0.60+α↑×0.40；S_score=β↓×0.55+γ↑×0.45；nsDiff=N-S（N需>+8才判定）\n'
        '  T_score=(β↓+β↑)÷2；F_score=γ↓×0.55+α↑×0.45；tfDiff=T-F\n'
        '  J_score=β↑×0.45+focus×0.55；P_score=θ×0.50+放鬆×0.50；jpDiff=J-P\n\n'
        '①【四軸腦波機制逐一解析】（每軸50字，共200字）\n'
        '  代入此人具體腦波數值計算每軸分數，說明「為何這組數字讓此人偏向此方向」\n'
        '  文獻：EI→Matthews & Gilliland(1999)α↑；NS→Rao & Singhania(2013)θ；\n'
        '  TF→Gallese(2001)γ↓鏡像神經；JP→Miller & Cohen(2001)β↑前額葉\n\n'
        '②【性格交互作用分析（2-3組，最重要）】（每組80字）\n'
        '  NT型→精確直覺+邏輯分析=策略洞察者；與NF(理想主義)或ST(現實執行)如何協作或誤解？\n'
        '  FJ型→共情+執行=溫暖推動者；在需要快速邏輯的場合如何感到衝突？\n'
        '  TJ型→邏輯+計畫=高效策略；與FP(共情+探索)如何在溝通方式上相互誤解？\n'
        '  根據此人具體型別，選出最相關2-3組，描述在工作/親密關係/獨處三場景的具體表現\n\n'
        '③【最模糊軸的雙面性格】（80字）\n'
        '  計算4個|diff|，找最小的一個軸——這是此人的雙面性格根源\n'
        '  說明此雙面性格在特定情境下如何自然切換，帶來什麼靈活性或困擾",'

        # 2-3 性格矛盾張力 × 情緒地雷
        '"2-3":"【v6.0 性格矛盾張力 × 情緒地雷定位】\n'
        '計算各軸邊界距（代入具體數值）：\n'
        '  EI邊界距=|(focus×0.35+γ↑×0.35+β↑×0.30)-(α↑×0.40+放鬆×0.30+α↓×0.30)|\n'
        '  NS邊界距=|(θ×0.60+α↑×0.40)-(β↓×0.55+γ↑×0.45)-8|\n'
        '  TF邊界距=|(β↓+β↑)/2-(γ↓×0.55+α↑×0.45)|\n'
        '  JP邊界距=|(β↑×0.45+focus×0.55)-(θ×0.50+放鬆×0.50)|\n'
        '  邊界距越小=矛盾越強、越容易在日常觸發\n\n'
        '①【性格主要矛盾分析】（200字）\n'
        '  找出邊界距最小的2個軸，描述：此人最常感到「一半想A一半想B」的內心拉扯\n'
        '  工作/親密關係/社交場合各一個具體的矛盾呈現場景\n'
        '  例：NS軸最小→直覺靈感vs事實數據的拉鋸；TF軸最小→堅守邏輯vs先顧情感\n\n'
        '②【情緒地雷定位（3-4個，根據主MBTI型別選取）】（200字）\n'
        '  N型地雷：被強迫「只看當下數據、不要想太遠」→θ通道被壓制，感到才能被否定\n'
        '  S型地雷：計畫模糊、被要求靠直覺行事→β↓受阻，α↓下降\n'
        '  T型地雷：情感優先於邏輯時→感到判斷力被質疑，lowBeta受阻\n'
        '  F型地雷：被批評「太感情用事」→lowGamma驟降，highBeta代償性升高\n'
        '  J型地雷：計畫突然被打亂或必須開放性等待→highBeta飆升、放鬆度崩跌\n'
        '  P型地雷：被強迫提前做最終決定→theta被壓制、α↓下降\n'
        '  E型地雷：長期獨處或沒有外部反饋→highGamma下降、focus失去錨點\n'
        '  I型地雷：頻繁社交、私人空間被侵入→highAlpha消耗殆盡、放鬆度崩潰\n'
        '  ——只選符合此人主MBTI的3-4個，引用具體腦波數值說明\n\n'
        '③【矛盾帶來的能量消耗與和解路徑】（80字）\n'
        '  說明矛盾如何消耗大腦能量（最強矛盾軸最耗神），並給出1個具體神經調節方法讓矛盾轉化為彈性",'

        # 2-4 壓力態變形 × 修復路徑
        '"2-4":"【壓力態性格變形 × 情緒觸發場景 × 修復路徑】\n'
        '計算：成熟穩定指數=α↓÷β↑（>1穩定；0.7-1中度；<0.7壓力敏感）；壓力張力=β↑-α↓\n'
        '壓力態轉換軸=邊界距最小的軸（同2-3），翻轉後即「陰影性格」\n\n'
        '①【最佳狀態（成熟面）描述】（80字）\n'
        '  α↓高且放鬆度充足時，此MBTI型最閃亮的3個性格特質是什麼？\n'
        '  引用具體α↓和放鬆度數值，評估此人目前距「最佳狀態」的位置\n\n'
        '②【壓力態性格變形路徑】（200字）\n'
        '  當β↑-α↓>20：v6.0規則——邊界距最小軸翻轉→出現「陰影型」\n'
        '  說明此人壓力下退行到哪個陰影性格？（列出具體MBTI型別）\n'
        '  陰影性格的具體行為樣貌：語言方式/與人互動/內心對白如何「不像自己」\n'
        '  引用具體β↑和α↓數值，評估目前的壓力態風險程度\n\n'
        '③【3個具體情緒地雷觸發場景】（150字）\n'
        '  延伸2-3節的地雷，寫出3個最真實的生活場景：\n'
        '  格式：「當[具體情境]時，你的[腦波指標]瞬間[上升/下降]，\n'
        '  你的反應可能是[具體行為]，這是你進入[陰影型]模式的訊號。」\n\n'
        '④【修復路徑（具體可執行）】（120字）\n'
        '  根據此人腦波特徵，提供從壓力態回到最佳態的2個具體修復方法：\n'
        '  每個方法說明：做什麼動作、持續多久、影響哪個腦波頻段、預期效果\n'
        '  例：每天早晨5分鐘深呼吸→降低β↑、提升α↓，7天後放鬆指數可回升5-10%"'
    )

    js = js[:old_start_idx] + new_dw_ch2 + js[old_end_idx:]
    patches_ok.append("Patch12_dw_ch2")
    print("  [OK]   Patch12_dw_ch2")

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
