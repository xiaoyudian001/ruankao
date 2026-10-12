"""Replay actual frozen answers without another model request or corpus change."""
import json
from pathlib import Path

from answer_citations import normalize_citations
from answer_cleanup import clean_answer

ROOT=Path(r'F:\daily\output\sysarch-citation-validation')
SOURCE=Path(r'F:\daily\output\sysarch-rag-evaluation\subquery-refined-20261009')


def main():
    records=[]
    for path in sorted(SOURCE.glob('Q*.json')):
        q=json.loads(path.read_text(encoding='utf-8'))
        cleaned=clean_answer(q['answer'])
        result=normalize_citations(cleaned,q['retrieved_chunks'])
        assert normalize_citations(result['text'],q['retrieved_chunks'])['text']==result['text'], 'Not idempotent'
        assert not result['invalid_ranks'] and not result['malformed_citations'],q['id']
        records.append({'id':q['id'],'question':q['question'],'before':q['answer'],'after':result['text'],
                        'diagnostics':{k:v for k,v in result.items() if k!='text'}})
    assert len(records)==20
    (ROOT/'replay.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 实际20题答案的引用回放','',
           '使用同次检索来源进行输出规范化，没有再次请求模型。正文和事实不改写；只证明来源格式与编号校验。','']
    for r in records:
        lines += [f'## {r["id"]}','',r['question'],'','### 原输出','',r['before'],'','### 校验后','',r['after'],'']
    (ROOT/'replay.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'questions':len(records),'changed_answers':sum(r['before']!=r['after'] for r in records),
                      'invalid_citations':sum(len(r['diagnostics']['invalid_ranks']) for r in records),
                      'unbound_page_mentions':{r['id']:r['diagnostics']['unbound_page_mentions'] for r in records if r['diagnostics']['unbound_page_mentions']}},ensure_ascii=False))


if __name__=='__main__':main()
