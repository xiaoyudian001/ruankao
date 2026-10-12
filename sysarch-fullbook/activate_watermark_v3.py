"""Switch only the QA flow's KB selector after verified V3 ingestion."""

import copy
import json
from pathlib import Path

from core import save_json_atomic
from langflow_api import LangflowAPI


ROOT = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')
FLOW_ID = '2e38f267-52d8-484f-bc4a-81ad7a2e3436'


def activate():
    verification = json.loads((ROOT / 'final_verification.json').read_text(encoding='utf-8'))
    assert verification['v2_chunks_unchanged'] == 1675
    assert verification['v3_chunks_verified'] == 1675
    assert verification['vector_backup_restored']
    assert verification['qa_answers_checked'] == 4
    api = LangflowAPI()
    flow = api.call('/flows/' + FLOW_ID)
    node = next(item for item in flow['data']['nodes'] if item['id'] == 'Knowledge-Y8gm2')
    template = node['data']['node']['template']
    if template['knowledge_base']['value'] == 'SysArchTutorRAGv3':
        print('ALREADY_ACTIVE')
        return
    assert template['knowledge_base']['value'] == 'SysArchTutorRAGv2'
    assert json.loads(template['metadata_filter']['value']) == {'section_type': 'body'}
    backup = ROOT / 'backups' / '教材检索与备考问答-before-v3-switch.json'
    if not backup.exists():
        save_json_atomic(backup, flow)
    original_data = copy.deepcopy(flow['data'])
    template['knowledge_base']['value'] = 'SysArchTutorRAGv3'
    options = template['knowledge_base'].get('options')
    if isinstance(options, list) and options and all(isinstance(value, str) for value in options):
        if 'SysArchTutorRAGv3' not in options:
            options.append('SysArchTutorRAGv3')
    assert api.call('/flows/' + FLOW_ID)['data'] == original_data, 'Concurrent flow edit detected'
    api.call('/flows/' + FLOW_ID, {'data': flow['data']}, 'PATCH')
    saved = api.call('/flows/' + FLOW_ID)
    actual = next(item for item in saved['data']['nodes'] if item['id'] == 'Knowledge-Y8gm2')
    values = actual['data']['node']['template']
    assert values['knowledge_base']['value'] == 'SysArchTutorRAGv3'
    assert json.loads(values['metadata_filter']['value']) == {'section_type': 'body'}
    save_json_atomic(ROOT / 'backups' / '教材检索与备考问答-after-v3-switch.json', saved)
    print('V3_ACTIVE', saved['name'])


if __name__ == '__main__':
    activate()
