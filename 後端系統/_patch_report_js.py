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
    # 6. Set L=2000 for all sections = max 2 pages per subsection.
    #    Previous state: L=k||c==="1-2"?9999:1050 → was patched to L=9999 (unlimited).
    #    Now set to 2000 (≈17px font × lineHeight2.0 → ~39 chars/line × ~25 lines × 2 pages).
    #    Applied in two passes because the JS may be in either state from a previous run.
    (
        'L=k||c==="1-2"?9999:1050',  # original state (if patch5 was never applied)
        'L=2000',
    ),
    (
        'L=9999,y=x',  # state after previous patch-6 run → update to 2000
        'L=2000,y=x',
    ),
    # 6b. Remove the l6() escape-hatch that would bypass L with X=9999 for list content.
    #     Without this fix, sections with bullet lists could still exceed 2 pages.
    (
        'const X=!k&&G.length>1e3&&l6(G)?9999:L;',
        'const X=L;',
    ),
    # 7. Fix q6 fallback filter to use same 80-char threshold as _chk5da.
    #    Old code only checks presence of "第X大" marker, not whether it has real content.
    #    This caused incomplete items to slip through and never get regenerated.
    (
        'const q6=["一","二","三","四","五"].filter(D=>!G.includes("第"+D+"大"));if(q6.length){',
        'const q6=["一","二","三","四","五"].filter((D,i,ar)=>{'
        'const s=(G||"").indexOf("第"+D+"大");'
        'if(s<0)return!0;'
        'const nx=i<4?(G||"").indexOf("第"+ar[i+1]+"大",s+1):-1;'
        'return(nx<0?(G||"").length:nx)-s<80});if(q6.length){',
    ),
    # 8. Fix retry-message missing-item detector to also use 80-char threshold.
    #    Without this fix, Gemini is told "nothing is missing" even when items have
    #    only echo-label text (<80 chars), so the retry prompt doesn't request them.
    (
        'filter(r=>!(G||"").includes("第"+r+"大")).join("、")||"第四、第五"}）',
        'filter((r,i,ar)=>{'
        'const s=(G||"").indexOf("第"+r+"大");'
        'if(s<0)return!0;'
        'const nx=i<4?(G||"").indexOf("第"+ar[i+1]+"大",s+1):-1;'
        'return(nx<0?(G||"").length:nx)-s<80}).join("、")||"第四大、第五大"}）',
    ),
    # 9. Increase retry attempts from 3 to 5 for sections 1-1 and 1-3
    #    (x=true for those sections), giving Gemini more chances to produce all 5 items.
    (
        'let G="";for(let D=0;D<3;D++){const fe=D>0?`',
        'let G="";for(let D=0;D<(x?5:3);D++){const fe=D>0?`',
    ),
    # 10. Add qeeg_* ability scores (0-100, population-normed) to the At brainwave object.
    #     These come from Ze (bw_b64 decoded payload) and replace eSense attention/meditation
    #     in sections that reference e.focus / e.relaxation.
    #     Applied AFTER patch #3 which already patched the end of the At object.
    (
        'mbti_profiles:Ze==null?void 0:Ze.mbti_profiles};',
        'mbti_profiles:Ze==null?void 0:Ze.mbti_profiles,'
        'qeeg_focus:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.focus,'
        'qeeg_relaxation:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.relaxation,'
        'qeeg_intuition:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.intuition,'
        'qeeg_energy:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.energy,'
        'qeeg_logic:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.logic,'
        'qeeg_awareness:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.awareness,'
        'qeeg_empathy:Ze==null?void 0:Ze.qeeg_abilities==null?void 0:Ze.qeeg_abilities.empathy};',
    ),
    # 11. When qeeg_focus is available on the At object, use it instead of raw attention
    #     for e.focus (which drives Ch1 strengths ranking, Ch7 focus sections, Ch9 stress).
    #     Similarly use qeeg_relaxation for e.relaxation.
    #     We override the focus/relaxation keys in the At object construction.
    #     The Ye() function reads from URL params; qeeg_focus/qeeg_relaxation are passed as URL params too.
    #     This patch updates focus and relaxation to prefer qeeg_* when present.
    (
        '"專注力",value:e.focus,color:"#2563eb"},{label:"放鬆度",value:e.relaxation,color:"#0d9488"}',
        '"專注力",value:e.qeeg_focus??e.focus,color:"#2563eb"},{label:"放鬆度",value:e.qeeg_relaxation??e.relaxation,color:"#0d9488"}',
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
