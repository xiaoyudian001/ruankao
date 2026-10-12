"""Replace only the never-run remote scorer experiment with offline CrossEncoder."""
import copy
import json
from langflow_api import LangflowAPI
from local_rerank_components import LOCAL_CODE
from setup_hybrid_flow import component, edge
from setup_rerank_flow import ROOT, PROTECTED, RANKER, MODEL, save
from run_rag_evaluation import flow_logic_fingerprint


def main():
    setup = json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
    api = LangflowAPI(); flow = api.call('/flows/'+setup['flow_id'])
    save(ROOT/'unused-remote-design-flow.json', flow)
    data = copy.deepcopy(flow['data'])
    old = next(n for n in data['nodes'] if n['id'] == RANKER)
    shared = {k: setup[k] for k in ('snapshot_path', 'snapshot_sha256')}
    local = component(api, LOCAL_CODE, RANKER, old['position'], {**shared, 'final_k': 5})
    data['nodes'] = [n for n in data['nodes'] if n['id'] not in {RANKER, MODEL}] + [local]
    data['edges'] = [e for e in data['edges'] if e['source'] not in {RANKER, MODEL} and e['target'] != RANKER]
    f = next(n for n in data['nodes'] if n['id'] == 'TextbookRRF-SysArch')
    types = local['data']['node']['outputs'][0]['types']
    data['edges'] += [
        edge('ChatInput-z2rit', 'ChatInput', 'message', ['Message'], RANKER, 'question', ['Message'], 'str'),
        edge(f['id'], f['data']['type'], 'fused_candidates', ['DataFrame'], RANKER, 'candidates', ['DataFrame', 'Table'], 'other'),
        edge(RANKER, local['data']['type'], 'reranked_candidates', types, 'parser-h3mx9', 'input_data', ['DataFrame', 'Table', 'Data', 'JSON'], 'other'),
        edge(RANKER, local['data']['type'], 'reranked_candidates', types, 'FinalAnswerCleaner-SysArch', 'reference_data', ['DataFrame', 'Table'], 'other'),
    ]
    api.call('/flows/'+setup['flow_id'], {'data': data,
       'description': '语义20＋BM25 20→RRF前20→本机多语言CrossEncoder重排序→前5证据→原MiniMax答案与出处校验；教材候选不发外部评分服务。'}, 'PATCH')
    actual = api.call('/flows/'+setup['flow_id'])
    assert actual['data'] == data
    save(ROOT/'experiment-flow.json', actual)
    setup.update({'rerank_engine': 'local_cross_encoder', 'model': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
                 'model_revision': '1427fd652930e4ba29e8149678df786c240d8825', 'rerank_timeout_seconds': 90,
                 'remote_design_executed': False, 'offline_inference': True})
    setup.pop('rerank_model_node', None); setup.pop('rerank_temperature', None)
    save(ROOT/'setup.json', setup)
    integrity = {label: flow_logic_fingerprint(api.call('/flows/'+fid)['data']) == flow_logic_fingerprint(
                 json.loads((ROOT/(label+'-before.json')).read_text(encoding='utf-8'))['data']) for label, fid in PROTECTED.items()}
    assert all(integrity.values()), integrity
    print(json.dumps({'flow_id': setup['flow_id'], 'engine': setup['rerank_engine'], 'nodes': len(data['nodes']),
                      'protected_flows_unchanged': integrity, 'remote_design_executed': False}, ensure_ascii=False))


if __name__ == '__main__': main()
