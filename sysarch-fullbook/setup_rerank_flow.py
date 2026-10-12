"""Create an isolated reranking experiment from the current hybrid flow."""
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from rerank_components import RERANK_CODE
from setup_hybrid_flow import component, edge
from run_rag_evaluation import flow_logic_fingerprint

ROOT = Path(r'F:\daily\output\sysarch-rerank')
PROTECTED = {'formal': '2e38f267-52d8-484f-bc4a-81ad7a2e3436',
             'hybrid': 'da6fd96e-f7fc-47fc-ae4f-e320febf0a6f',
             'subquery': '730d9bd5-e084-4b32-814e-edea8d404c4b'}
RANKER = 'TextbookReranker-SysArch'
MODEL = 'RerankModel-SysArch'


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT/'setup.json').exists():
        print((ROOT/'setup.json').read_text(encoding='utf-8')); return
    api = LangflowAPI()
    protected = {label: api.call('/flows/'+fid) for label, fid in PROTECTED.items()}
    for label, flow in protected.items(): save(ROOT/(label+'-before.json'), flow)
    original = protected['hybrid']; data = copy.deepcopy(original['data'])
    nodes = {n['id']: n for n in data['nodes']}
    fusion = nodes['TextbookRRF-SysArch']
    shared = {k: fusion['data']['node']['template'][k]['value'] for k in ('snapshot_path', 'snapshot_sha256')}
    fusion['data']['node']['template']['final_k']['value'] = 20
    fusion['data']['node']['display_name'] = '融合候选 RRF · 前20片'
    ranker = component(api, RERANK_CODE, RANKER, {'x': 1100, 'y': 700}, {**shared, 'final_k': 5})
    model = copy.deepcopy(nodes['LanguageModelComponent-BpTTF'])
    model['id'] = MODEL; model['data']['id'] = MODEL
    model['data']['selected_output'] = 'model_output'
    model['data']['node']['display_name'] = 'MiniMax 相关性评分模型'
    model['position'] = {'x': 100, 'y': 1000}
    for k, v in {'temperature': 0., 'max_tokens': 4096, 'input_value': '', 'system_message': '', 'stream': False}.items():
        model['data']['node']['template'][k]['value'] = v
    data['nodes'] += [ranker, model]
    data['edges'] = [e for e in data['edges'] if not (e['source'] == fusion['id'] and e['target'] in {'parser-h3mx9', 'FinalAnswerCleaner-SysArch'})]
    types = ranker['data']['node']['outputs'][0]['types']
    data['edges'] += [
        edge('ChatInput-z2rit', 'ChatInput', 'message', ['Message'], RANKER, 'question', ['Message'], 'str'),
        edge(fusion['id'], fusion['data']['type'], 'fused_candidates', ['DataFrame'], RANKER, 'candidates', ['DataFrame', 'Table'], 'other'),
        edge(MODEL, model['data']['type'], 'model_output', ['LanguageModel'], RANKER, 'rerank_model', ['LanguageModel'], 'other'),
        edge(RANKER, ranker['data']['type'], 'reranked_candidates', types, 'parser-h3mx9', 'input_data', ['DataFrame', 'Table', 'Data', 'JSON'], 'other'),
        edge(RANKER, ranker['data']['type'], 'reranked_candidates', types, 'FinalAnswerCleaner-SysArch', 'reference_data', ['DataFrame', 'Table'], 'other'),
    ]
    positions = {'parser-h3mx9': (1600, 700), 'Prompt Template-fzcHC': (1600, 1120),
                 'LanguageModelComponent-BpTTF': (1100, 1470), 'FinalAnswerCleaner-SysArch': (1600, 1680), 'ChatOutput-QRg8s': (1100, 1970)}
    for nid, (x, y) in positions.items(): nodes[nid]['position'] = {'x': x, 'y': y}
    for n in data['nodes']:
        n['selected'] = False; n['data']['selected'] = False
    data['viewport'] = {'x': 10, 'y': 10, 'zoom': .4}
    downstream = {'parser-h3mx9', 'Prompt Template-fzcHC', 'LanguageModelComponent-BpTTF', 'FinalAnswerCleaner-SysArch', 'ChatOutput-QRg8s'}
    for nid in downstream:
        before = next(n for n in original['data']['nodes'] if n['id'] == nid)
        assert nodes[nid]['data']['node']['template'] == before['data']['node']['template'], nid
    for target in ('parser-h3mx9', 'FinalAnswerCleaner-SysArch'):
        assert any(e['source'] == RANKER and e['target'] == target for e in data['edges'])
    new = api.call('/flows/', {'name': '教材检索与备考问答 · 混合检索重排序实验',
        'description': '语义20＋BM25 20→RRF前20→MiniMax批量相关性评分→前5证据→原答案与出处校验；失败回退RRF，网页未切换。',
        'folder_id': original['folder_id'], 'data': data}, 'POST')
    # Save identity immediately so an interrupted verification cannot create duplicates.
    save(ROOT/'setup.json', {'flow_id': new['id'], 'flow_name': new['name'], 'source_flow_id': PROTECTED['hybrid'],
        'candidate_k': 20, 'final_k': 5, 'rerank_node': RANKER, 'rerank_model_node': MODEL,
        'rerank_temperature': 0, 'rerank_timeout_seconds': 60, 'website_switched': False, **shared})
    actual = api.call('/flows/'+new['id'])
    assert actual['data'] == data
    save(ROOT/'experiment-flow.json', actual)
    integrity = {label: flow_logic_fingerprint(api.call('/flows/'+PROTECTED[label])['data']) == flow_logic_fingerprint(flow['data'])
                 for label, flow in protected.items()}
    assert all(integrity.values()), integrity
    save(ROOT/'setup-verification.json', {'protected_flows_unchanged': integrity, 'nodes': len(data['nodes']), 'edges': len(data['edges'])})
    print((ROOT/'setup.json').read_text(encoding='utf-8'))


if __name__ == '__main__': main()
