"""Patch script for report-app: MBTI unification + content completeness fixes."""
import pathlib

p = pathlib.Path(__file__).parent / "static-app/report-app/assets/index-CqHWGLJp.js"
t = p.read_text(encoding="utf-8")

patches = [
    # 1. Default to 8-gua (含離卦)
    ("function Ux(a,r=!1){", "function Ux(a,r=!0){"),
    # 2. wu() uses server-precomputed MBTI when present in brainwave payload
    (
        "function wu(a){const r=Ux({",
        "function wu(a){if(a.mbti_primary){const _mp=a.mbti_primary,"
        "[_ml,_md]=F5[_mp]??['未知型',''],"
        "_ms=(a.mbti_secondaries??[]).map(s=>{const[c,l]=F5[s.mbti]??['未知型',''];"
        "return{type:s.mbti,label:c,desc:l,strength:s.strength,reason:s.reason}});"
        "return{type:_mp,ei:(a.mbti_ei??50)-50,ns:(a.mbti_ns??50)-50,"
        "tf:(a.mbti_tf??50)-50,jp:(a.mbti_jp??50)-50,label:_ml,desc:_md,"
        "bagua:a.mbti_bagua||'',baguaName:a.mbti_bagua_name||'',"
        "mindColorName:a.mindColorName||'',secondaries:_ms}}const r=Ux({",
    ),
    # 3. Pass mbti fields from bw_b64 payload into At brainwave object
    (
        'lowGamma:et(["low_gamma","gamma_low"],Ye("lowGamma",50))};',
        'lowGamma:et(["low_gamma","gamma_low"],Ye("lowGamma",50)),'
        'mbti_primary:Ze==null?void 0:Ze.mbti_primary,'
        'mbti_ei:Ze==null?void 0:Ze.mbti_ei,mbti_ns:Ze==null?void 0:Ze.mbti_ns,'
        'mbti_tf:Ze==null?void 0:Ze.mbti_tf,mbti_jp:Ze==null?void 0:Ze.mbti_jp,'
        'mbti_bagua:Ze==null?void 0:Ze.mbti_bagua,'
        'mbti_bagua_name:Ze==null?void 0:Ze.mbti_bagua_name,'
        'mbti_secondaries:Ze==null?void 0:Ze.mbti_secondaries,'
        'mbti_profiles:Ze==null?void 0:Ze.mbti_profiles};',
    ),
    # 4. Fix _chk5da: require each item section to have >=80 chars of real content,
    #    not just the "第X大" marker (prevents Gemini echo-labels from falsely passing).
    (
        'function _chk5da(a){return!!a&&["一","二","三","四","五"].every(r=>a.includes("第"+r+"大"))}',
        'function _chk5da(a){if(!a)return!1;'
        'return["一","二","三","四","五"].every((r,i,ar)=>{'
        'const s=a.indexOf("第"+r+"大");'
        'if(s<0)return!1;'
        'const nx=i<4?a.indexOf("第"+ar[i+1]+"大",s+1):-1;'
        'return(nx<0?a.length:nx)-s>=80})}',
    ),
    # 5. Fix section 1-2 truncation: include "1-2" in L=9999 set so the advice
    #    content is never cut off by the 1050-char ym() limit.
    (
        'L=k?9999:1050',
        'L=k||c==="1-2"?9999:1050',
    ),
]

for old, new in patches:
    if old not in t:
        print(f"MISSING: {old[:60]}...")
    else:
        t = t.replace(old, new, 1)
        print(f"OK: {old[:50]}...")

p.write_text(t, encoding="utf-8")
print("Done.")
