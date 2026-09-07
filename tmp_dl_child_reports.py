import requests, json

data = json.load(open('_tmp_child_reports.json', encoding='utf-8'))
for c in data:
    rid = c['report_id']
    print(rid, c['subject_name'], c['completed_at'])
    resp = requests.get(c['pdf_url'], timeout=60)
    fn = f'_tmp_child_{rid}.pdf'
    with open(fn, 'wb') as f:
        f.write(resp.content)
    print('  saved', fn, len(resp.content), 'bytes')
