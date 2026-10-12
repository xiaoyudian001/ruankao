"""Restore only the two experimental code fields; preserve current UI state."""
import copy
import json
from langflow_api import LangflowAPI
from audit_planner_v2 import ROOT, FLOWS
from run_rag_evaluation import flow_logic_fingerprint


def main():
    manifest = json.loads((ROOT/'activation.json').read_text(encoding='utf-8'))
    rollback = json.loads((ROOT/'experiment-rollback.json').read_text(encoding='utf-8'))['data']
    api = LangflowAPI()
    current = api.call('/flows/'+FLOWS['experiment'])['data']
    assert flow_logic_fingerprint(current) == manifest['after_logic_sha256'], 'Experiment changed; inspect before rollback'
    result = copy.deepcopy(current)
    old = {n['id']: n for n in rollback['nodes']}
    for n in result['nodes']:
        if n['id'] in manifest['changed_nodes']:
            n['data']['node']['template']['code']['value'] = old[n['id']]['data']['node']['template']['code']['value']
    api.call('/flows/'+FLOWS['experiment'], {'data': result}, 'PATCH')
    assert api.call('/flows/'+FLOWS['experiment'])['data'] == result
    print('Restored two experimental code fields. Formal/hybrid flows and website unchanged.')


if __name__ == '__main__':
    main()
