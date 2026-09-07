f = open('後端系統/static-app/app_prototype.html', encoding='utf-8')
lines = f.readlines()
f.close()

# Find the exact line range to replace
start_marker = "      const bwBtn = isSuccess"
end_marker = "          <div id=\"bw-detail-"

start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if start_marker in line and start_idx is None:
        start_idx = i
    if end_marker in line and start_idx is not None and end_idx is None:
        end_idx = i
        break

print(f"start_idx={start_idx}, end_idx={end_idx}")
print(f"start line: {lines[start_idx].rstrip()}")
print(f"end line: {lines[end_idx].rstrip()}")

# Build replacement lines
replacement = [
    "\n",
    "      // 計算此受測者在 _historyCache 中的累計統計\n",
    "      const subjSessions = _historyCache.filter(x => x.subject_name === s.subject_name);\n",
    "      const subjTotalSessions = subjSessions.length;\n",
    "      const subjDoneReports = subjSessions.filter(x => x.report_status === 'completed').length;\n",
    "      const genderLabel = s.subject_gender === 'M' ? '男' : s.subject_gender === 'F' ? '女' : (s.subject_gender || '');\n",
    "\n",
    "      html += `\n",
    "        <div class=\"history-item\" style=\"margin:0 0 10px;${isSuccess ? '' : 'opacity:0.7;'}\">\n",
    "          <div class=\"hi-top\">\n",
    "            <span class=\"hi-name\">${s.subject_name || '—'}${subjAge}${genderLabel ? ' · ' + genderLabel : ''}</span>\n",
    "            ${statusTag}\n",
    "          </div>\n",
    "          ${reportTagsHtml}\n",
    "          ${extraNote}\n",
    "          <div style=\"font-size:11px;color:#bbb;margin-top:6px;\">${dateStr}${captures} ${bdnaModeLabel}</div>\n",
    "          <div style=\"display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap;\">\n",
    "            <button onclick=\"_viewSubjectDetail(${s.session_id}, ${subjTotalSessions}, ${subjDoneReports})\"\n",
    "              style=\"background:#e8f0fe;color:#1a3a6e;border:none;font-size:12px;padding:5px 10px;border-radius:8px;font-weight:600;cursor:pointer;\">\n",
    "              📋 受測者資料\n",
    "            </button>\n",
    "          </div>\n",
    "          <!-- 受測者資料展開區（預設隱藏）-->\n",
    "          <div id=\"subj-detail-${s.session_id}\" style=\"display:none;margin-top:10px;\"></div>\n",
    "        </div>`;\n",
]

new_lines = lines[:start_idx] + replacement + lines[end_idx+1:]

with open('後端系統/static-app/app_prototype.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print(f'Done. Original lines: {len(lines)}, New lines: {len(new_lines)}')
