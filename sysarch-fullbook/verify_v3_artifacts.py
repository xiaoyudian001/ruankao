"""Independent checks before using the cleaned knowledge base in the QA flow."""

import json
import re
from pathlib import Path

from core import save_json_atomic
from langflow_api import LangflowAPI
from verify_qa import answer_text, context_text


V2 = Path(r'F:\daily\output\sysarch-fullbook-v2')
V3 = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')


def verify():
    old = json.loads((V2 / 'final_chunks.json').read_text(encoding='utf-8'))
    new = json.loads((V3 / 'final_chunks.json').read_text(encoding='utf-8'))
    assert len(old) == len(new) == 1675
    changed = []
    for before, after in zip(old, new):
        assert before['id'] == after['id']
        if before['content'] != after['content']:
            changed.append(before['metadata']['pdf_pages'])
        for key in ('pdf_pages', 'pdf_page_start', 'pdf_page_end', 'chapter',
                    'source_file', 'source_sha256', 'section_type', 'batch_id'):
            assert before['metadata'].get(key) == after['metadata'].get(key)
    assert len(changed) == 10
    assert not any(term in row['content'] for row in new
                   for term in ('文老师', '淘宝搜索', '宝搜索'))
    assert any('天猫淘宝' in row['content'] for row in new)
    assert (V3 / 'backups' / 'SysArchTutorRAGv3-backup-verification.json').exists()
    backup = json.loads((V3 / 'backups' / 'SysArchTutorRAGv3-backup-verification.json').read_text(encoding='utf-8'))
    assert backup['count'] == 1675 and backup['restored_contents_metadata_vectors_match']

    api = LangflowAPI()
    assert api.call('/knowledge_bases/SysArchTutorRAGv2')['chunks'] == 1675
    assert api.call('/knowledge_bases/SysArchTutorRAGv3')['chunks'] == 1675
    v2_stored = {item['metadata']['chunk_id']: item for item in api.chunks('SysArchTutorRAGv2')}
    assert len(v2_stored) == 1675
    assert all(v2_stored[row['metadata']['chunk_id']]['content'] == row['content'] for row in old)

    qa = V3 / 'qa_tests'
    narrowed = []
    for index in range(1, 5):
        context = context_text(json.loads((qa / f'{index}-context.json').read_text(encoding='utf-8')))
        answer = answer_text(json.loads((qa / f'{index}-answer.json').read_text(encoding='utf-8')))
        sources = {int(rank): (int(start), int(end or start))
                   for rank, start, end in re.findall(
                       r'\[片段(\d+)\]\s*来源：[^\n]*?原PDF第(\d+)(?:～(\d+))?页', context)}
        citations = [(int(rank), int(start), int(end or start))
                     for rank, start, end in re.findall(
                         r'\[片段(\d+)[^\]\n]*?原PDF第(\d+)(?:[～—–\-至](\d+))?页[^\]\n]*\]', answer)]
        assert citations, f'No citations in QA answer {index}'
        for rank, start, end in citations:
            assert rank in sources and sources[rank][0] <= start <= end <= sources[rank][1]
            if (start, end) != sources[rank]:
                narrowed.append({'qa': index, 'fragment': rank,
                                 'source_range': sources[rank], 'answer_range': [start, end]})

    result = {'v2_chunks_unchanged': 1675, 'v3_chunks_verified': 1675,
              'changed_chunk_count': len(changed), 'changed_chunk_pages': changed,
              'vector_backup_restored': True, 'qa_answers_checked': 4,
              'citations_within_source_pages': True, 'narrowed_citations': narrowed}
    save_json_atomic(V3 / 'final_verification.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    verify()
