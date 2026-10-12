"""Verify saved parent/Parser/cleaner wiring and one actual answer, without changing flows."""
import asyncio
import inspect
import json
import re
import sys
import time
from pathlib import Path

from activate_source_references import FLOWS
from core import save_json_atomic
from langflow_api import LangflowAPI
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from parent_context import load_parent_index

ROOT = Path(r'F:\daily\output\sysarch-parent-context')


def instance(node):
    code = node['data']['node']['template']['code']['value']
    scope = {}
    exec(compile(code, '<saved-component>', 'exec'), scope)
    name = re.findall(r'^class (\w+)\([^\n]*Component[^\n]*\):', code, re.M)[-1]
    return scope[name](_code=code)


def main():
    api = LangflowAPI()
    settings = json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
    index = load_parent_index(settings['index_path'], settings['index_sha256'])
    entry = next(e for e in index['children'].values()
                 if len(index['parents'][e['parent_id']]['child_ids']) == 3)
    hit = entry['row']
    checks = []
    for label, fid in FLOWS.items():
        data = api.call('/flows/'+fid)['data']
        nodes = {n['id']: n for n in data['nodes']}
        parent = instance(nodes['TextbookParentContext-SysArch'])
        parent.set(hits=DataFrame([hit]), enabled=True, max_chars=10000, max_sources=10,
                   index_path=settings['index_path'], index_sha256=settings['index_sha256'])
        expanded = parent.expand()
        rows = expanded.to_dict(orient='records')
        trace = rows[0]['context_expansion_trace']
        assert trace['route'] == 'expanded' and len(rows) == 3, trace
        assert [r['rag_rank'] for r in rows] == [1,2,3]
        parent_edges = [e for e in data['edges'] if e['source']=='TextbookParentContext-SysArch']
        assert {(e['target'], e['data']['targetHandle']['fieldName']) for e in parent_edges} == {
            ('parser-h3mx9', 'input_data'), ('FinalAnswerCleaner-SysArch', 'reference_data')}
        parser_node = nodes['parser-h3mx9']
        parser = instance(parser_node)
        fields = parser_node['data']['node']['template']
        values = {k: fields[k]['value'] for k in ('pattern','sep','mode') if k in fields}
        parser.set(input_data=expanded, **values)
        method = parser_node['data']['node']['outputs'][0]['method']
        parsed = getattr(parser, method)()
        if inspect.isawaitable(parsed):
            parsed = asyncio.run(parsed)
        context = parsed.text
        for row in rows:
            assert row['content'] in context
            assert row['context_hint'] in context
            assert f"[片段{row['rag_rank']}]" in context
        cleaner = instance(nodes['FinalAnswerCleaner-SysArch'])
        cleaner.set(input_message=Message(text='定义。[片段1] 补充条件。[片段2][片段3]'),
                    reference_data=expanded)
        output = cleaner.clean_message()
        refs = output.session_metadata['textbook_refs']
        assert len(refs)==3
        for row, ref in zip(rows, refs):
            assert ref['rank']==row['rag_rank'] and ref['chunkId']==row['chunk_id']
            assert ref['content']==row['content']
            assert ref['pdfPages']==list(range(int(row['pdf_page_start']), int(row['pdf_page_end'])+1))
        parent.set(index_sha256='0'*64)
        fallback = parent.expand().to_dict(orient='records')
        assert len(fallback)==1 and fallback[0]['content']==hit['content']
        assert fallback[0]['context_expansion_trace']['route']=='retrieval_only_fallback'
        checks.append({'flow':label,'expanded_rows':len(rows),'context_chars':trace['context_chars'],
                       'parser_and_snapshot_match':True,'invalid_index_fallback':True})
        print(json.dumps(checks[-1], ensure_ascii=False), flush=True)
    save_json_atomic(ROOT/'component-verification.json', {'checks': checks})
    if '--live' in sys.argv:
        sys.path.insert(0, r'F:\daily\textbook-bridge')
        from bridge import LocalFlow
        start = time.monotonic()
        result = LocalFlow().run_with_sources({
            'question':'教材如何定义MTTF、MTTR和MTBF？请说明各自含义、适用条件和相互关系，并给出教材出处。',
            'session_id':'verify-parent-20261010','retrieval_mode':'complete'})
        result['elapsed_seconds'] = round(time.monotonic()-start,2)
        assert result['answer'].strip() and 5 < len(result['references']) <= 10, 'No expanded source snapshots'
        ranks = {r['rank'] for r in result['references']}
        cited = {int(n) for n in re.findall(r'\[片段\s*(\d+)', result['answer'])}
        assert cited and cited <= ranks, 'Citation missing source snapshot'
        save_json_atomic(ROOT/'flow-verification.json', result)
        print(json.dumps({'live_flow':'complete','references':len(result['references']),
                          'cited_ranks':sorted(cited),'elapsed_seconds':result['elapsed_seconds']},ensure_ascii=False))


if __name__ == '__main__':
    main()
