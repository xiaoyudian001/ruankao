"""Patch only planner and its duplicate boundary validator in the experiment."""
import copy
import argparse
import hashlib
import json
from pathlib import Path
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint
from setup_hybrid_flow import component
from subquery_components import PLANNER_CODE, RETRIEVER_CODE
from audit_planner_v2 import FLOWS, ROOT, difference_paths


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    assert args.refresh or not (ROOT/'activation.json').exists(), 'Already activated; inspect before refresh'
    api = LangflowAPI()
    before = {label: api.call('/flows/'+fid) for label, fid in FLOWS.items()}
    for label in ('formal', 'hybrid'):
        assert flow_logic_fingerprint(before[label]['data']) == flow_logic_fingerprint(load(ROOT/(label+'-before.json'))['data'])
    original = before['experiment']['data']
    if args.refresh:
        previous = load(ROOT/'activation.json')
        assert flow_logic_fingerprint(original) == previous['after_logic_sha256'], 'Concurrent experiment edit'
        differences = previous['baseline_nonfunctional_drift']
        (ROOT/'activation-before-ascii-fix.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        baseline = load(Path(r'F:\daily\output\sysarch-rag-evaluation\planner-v1-citation-baseline-20261009\evaluated-flow.json'))
        differences = difference_paths(baseline, original)
        assert all(p.startswith('/viewport/') or p.endswith('/selected') or p.endswith('/lf_version') for p in differences), differences
    data = copy.deepcopy(original)
    nodes = {n['id']: n for n in data['nodes']}
    codes = {'TextbookQueryPlanner-SysArch': PLANNER_CODE, 'Knowledge-Y8gm2': RETRIEVER_CODE}
    old_retriever = nodes['Knowledge-Y8gm2']['data']['node']['template']['code']['value']
    assert old_retriever.split('        index = load_snapshot', 1)[1] == RETRIEVER_CODE.split('        index = load_snapshot', 1)[1], 'Retrieval implementation changed'
    for nid, code in codes.items():
        node = nodes[nid]
        compiled = component(api, code, nid, node['position'], {})
        previous_inputs = set(node['data']['node']['template']) - {'_type'}
        new_inputs = set(compiled['data']['node']['template']) - {'_type'}
        assert previous_inputs == new_inputs, 'Component input schema changed'
        assert [o['name'] for o in node['data']['node']['outputs']] == [o['name'] for o in compiled['data']['node']['outputs']]
        node['data']['node']['template']['code']['value'] = code
    restored = copy.deepcopy(data)
    originals = {n['id']: n for n in original['nodes']}
    for n in restored['nodes']:
        if n['id'] in codes:
            n['data']['node']['template']['code']['value'] = originals[n['id']]['data']['node']['template']['code']['value']
    assert restored == original, 'Changes outside two code fields'
    if not args.refresh:
        (ROOT/'experiment-rollback.json').write_text(json.dumps(before['experiment'], ensure_ascii=False, indent=2), encoding='utf-8')
    # Reading the full set here provides a before/after integrity comparison.
    if not args.refresh:
        (ROOT/'kb-before.json').write_text(json.dumps(api.chunks('SysArchTutorRAGv3'), ensure_ascii=False, indent=2), encoding='utf-8')
    assert flow_logic_fingerprint(api.call('/flows/'+FLOWS['experiment'])['data']) == flow_logic_fingerprint(original), 'Concurrent edit'
    api.call('/flows/'+FLOWS['experiment'], {'data': data}, 'PATCH')
    saved = api.call('/flows/'+FLOWS['experiment'])
    assert saved['data'] == data, 'Save did not match'
    (ROOT/'experiment-after.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    protected = {}
    for label in ('formal', 'hybrid'):
        protected[label] = flow_logic_fingerprint(api.call('/flows/'+FLOWS[label])['data']) == flow_logic_fingerprint(before[label]['data'])
        assert protected[label]
    manifest = {'flow_id': FLOWS['experiment'], 'before_logic_sha256': previous['before_logic_sha256'] if args.refresh else flow_logic_fingerprint(original),
                'after_logic_sha256': flow_logic_fingerprint(data), 'protected_flows': protected,
                'changed_nodes': list(codes), 'changed_fields': ['template.code.value'],
                'baseline_nonfunctional_drift': differences,
                'retrieval_backend_unchanged': True, 'answer_generation_and_citations_unchanged': True,
                'extra_model_calls': 0, 'website_target_not_changed': True,
                'english_identifier_boundary_fix': True,
                'source_hashes': {nid: hashlib.sha256(code.encode()).hexdigest() for nid, code in codes.items()}}
    (ROOT/'activation.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
