f = open('後端系統/static-app/app_prototype.html', encoding='utf-8')
content = f.read()
f.close()

# Fix 1: remove duplicate closing line (the old one that wasn't removed)
# Line 3737 is `        </div>\`;` (new correct one)
# Line 3738 is `        </div>\`;` (old duplicate)
content = content.replace(
    "        </div>`;\n        </div>`;\n    });\n  });\n  c.innerHTML = html;\n}",
    "        </div>`;\n    });\n  });\n  c.innerHTML = html;\n}"
)

# Fix 2: replace _viewHistorySession with _viewSubjectDetail
old_func_start = "// 點「🧠 查看腦波」：從後端取該 Session 的腦波統計，展開在卡片下方\n// 同時把 window._lastEegCapture 設為這筆，方便「切換到結果頁」時顯示正確腦波\nasync function _viewHistorySession(sessionId) {"
old_func_end = "  } catch (e) {\n    detailEl.innerHTML = `<span style=\"color:#c00;\">❌ 載入失敗：${e.message}</span>`;\n  }\n}"

# Find the full function span
start_pos = content.find(old_func_start)
end_str = "  } catch (e) {\n    detailEl.innerHTML = `<span style=\"color:#c00;\">❌ 載入失敗：${e.message}</span>`;\n  }\n}"
end_pos = content.find(end_str, start_pos)

if start_pos == -1:
    print("ERROR: Could not find _viewHistorySession function start")
elif end_pos == -1:
    print("ERROR: Could not find _viewHistorySession function end")
else:
    end_pos += len(end_str)
    print(f"Found function at pos {start_pos}–{end_pos}")
    
    new_func = """// 點「📋 受測者資料」：展開顯示受測者基本資料及歷史統計（不顯示腦波數值）
function _viewSubjectDetail(sessionId, totalSessions, doneReports) {
  const detailEl = document.getElementById(`subj-detail-${sessionId}`);
  if (!detailEl) return;

  // toggle：已顯示就收起
  if (detailEl.style.display !== 'none') {
    detailEl.style.display = 'none';
    return;
  }

  // 從 _historyCache 找到對應的 session 資料
  const sess = _historyCache.find(x => x.session_id === sessionId);
  if (!sess) { detailEl.style.display = 'block'; detailEl.innerHTML = '<span style="color:#aaa;">無資料</span>'; return; }

  const lbl = _historyReportLabel(sess.report_type);
  const genderLabel = sess.subject_gender === 'M' ? '男' : sess.subject_gender === 'F' ? '女' : (sess.subject_gender || '—');
  const capturesStr = sess.total_captures ? `${sess.total_captures} 筆` : '—';
  const dateStr = _formatTs(sess.created_at);

  // 報告狀態顯示
  const reportStatusMap = {
    'completed': '<span style="color:#2e7d32;font-weight:700;">✅ 報告已完成</span>',
    'processing': '<span style="color:#f57c00;font-weight:700;">⏳ 生成中</span>',
    'failed':    '<span style="color:#c62828;font-weight:700;">❌ 生成失敗</span>',
  };
  const reportStatusHtml = reportStatusMap[sess.report_status] || '<span style="color:#888;">— 尚未生成</span>';

  // 此受測者所有歷史 sessions（依時間排序，新→舊）
  const subjSessions = _historyCache
    .filter(x => x.subject_name === sess.subject_name)
    .sort((a, b) => (b.created_at || 0) - (a.created_at || 0));

  const historyRows = subjSessions.map(x => {
    const xLbl = _historyReportLabel(x.report_type);
    const xDate = _formatTs(x.created_at);
    const xStatus = x.report_status === 'completed' ? '✅' : x.status === 0 ? '❌' : '○';
    const isThis = x.session_id === sessionId ? 'font-weight:700;color:#1a3a6e;' : 'color:#555;';
    return `<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #e8eef4;${isThis}">
      <span style="flex:0 0 18px;text-align:center;">${xStatus}</span>
      <span style="flex:1;font-size:11px;">${xLbl.icon} ${xLbl.name}</span>
      <span style="flex:0 0 auto;font-size:11px;color:#999;">${xDate}</span>
    </div>`;
  }).join('');

  detailEl.style.display = 'block';
  detailEl.innerHTML = `
    <div style="background:#f0f4f8;border-radius:10px;padding:12px 14px;font-size:12px;">
      <div style="font-weight:700;color:#1a3a6e;font-size:13px;margin-bottom:10px;">👤 受測者基本資料</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin-bottom:12px;">
        <div><span style="color:#999;">姓名</span><br><strong>${sess.subject_name || '—'}</strong></div>
        <div><span style="color:#999;">年齡</span><br><strong>${sess.subject_age ? sess.subject_age + ' 歲' : '—'}</strong></div>
        <div><span style="color:#999;">性別</span><br><strong>${genderLabel}</strong></div>
        <div><span style="color:#999;">本次採樣</span><br><strong>${capturesStr}</strong></div>
        <div><span style="color:#999;">報告類型</span><br><strong>${lbl.icon} ${lbl.name}</strong></div>
        <div><span style="color:#999;">報告狀態</span><br>${reportStatusHtml}</div>
      </div>
      <div style="font-weight:700;color:#1a3a6e;font-size:12px;margin-bottom:6px;">
        📊 歷史紀錄（共 ${totalSessions} 次檢測 · ${doneReports} 份報告完成）
      </div>
      <div style="max-height:160px;overflow-y:auto;">${historyRows}</div>
    </div>`;
}"""
    
    content = content[:start_pos] + new_func + content[end_pos:]
    print("Replaced _viewHistorySession with _viewSubjectDetail")

with open('後端系統/static-app/app_prototype.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done.")
