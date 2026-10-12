"""Repair only the complete flow's final cleaner source, preserving all settings and edges."""
import copy
import json
from datetime import datetime
from pathlib import Path

from activate_source_references import FLOWS
from citation_validation_component import cleaner_code
from langflow_api import LangflowAPI
from setup_hybrid_flow import digest


def main():
    api = LangflowAPI()
    before = {label: api.call('/flows/'+fid)['data'] for label, fid in FLOWS.items()}
    original = before['complete']
    data = copy.deepcopy(original)
    node = next(n for n in data['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
    field = node['data']['node']['template']['code']
    old_code = field['value']
    field['value'] = cleaner_code(old_code)
    restored = copy.deepcopy(data)
    next(n for n in restored['nodes'] if n['id']==node['id'])['data']['node']['template']['code']['value'] = old_code
    assert restored == original, 'Unexpected changes outside cleaner source'
    assert 'session_metadata' in field['value'] and 'textbook_refs' in field['value']
    root = Path(r'F:\daily\output\sysarch-citation-viewer\complete-repair')
    root.mkdir(parents=True, exist_ok=True)
    tag = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = root/(tag+'-before.json')
    backup.write_text(json.dumps(original, ensure_ascii=False), encoding='utf-8')
    assert api.call('/flows/'+FLOWS['complete'])['data'] == original, 'Concurrent flow edit'
    api.call('/flows/'+FLOWS['complete'], {'data':data}, 'PATCH')
    assert api.call('/flows/'+FLOWS['complete'])['data'] == data
    for label, fid in FLOWS.items():
        if label != 'complete':
            assert api.call('/flows/'+fid)['data'] == before[label], 'Other flow changed: '+label
    report = {'flow':FLOWS['complete'], 'backup':str(backup), 'before_sha':digest(original),
              'after_sha':digest(data), 'change':'final cleaner source only', 'other_flows_unchanged':True}
    (root/'activation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
