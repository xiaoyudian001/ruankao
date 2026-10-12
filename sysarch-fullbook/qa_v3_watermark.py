"""Check retrieval and answers against the cleaned, page-cited corpus."""

import json
import re
from pathlib import Path

from core import save_json_atomic
from langflow_api import LangflowAPI
from verify_qa import answer_text, context_text


ROOT = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')
QA_FLOW = '2e38f267-52d8-484f-bc4a-81ad7a2e3436'
QUESTIONS = [
    ('高级架构师', '依据教材，高级架构设计师与中级架构设计师的典型区别是什么？',
     ['创造'], {37, 38}),
    ('Web服务器', '依据教材，Web服务器性能评估有哪些主要指标？',
     ['并发', '延迟', '吞吐'], {119}),
    ('风险计算', '依据教材，信息资产的风险计算过程有哪些步骤？',
     ['资产', '威胁', '脆弱'], {189}),
    ('事件驱动', '依据教材，事件驱动架构由哪四个部分组成？',
     ['事件队列', '分发器', '事件通道', '事件处理器'], {24, 25, 26}),
]


def call_flow(api, question, output_component, session_id):
    body = {'input_request': {
        'input_value': question, 'input_type': 'chat', 'output_type': 'chat',
        'output_component': output_component,
        'tweaks': {'Knowledge-Y8gm2': {
            'knowledge_base': 'SysArchTutorRAGv3',
            'metadata_filter': json.dumps({'section_type': 'body'})},
            'ChatInput-z2rit': {'should_store_message': False},
            'ChatOutput-QRg8s': {'should_store_message': False}},
        'session_id': session_id}}
    return api.call('/run/session/' + QA_FLOW, body, 'POST', timeout=180)


def verify():
    api = LangflowAPI()
    assert api.call('/knowledge_bases/SysArchTutorRAGv3')['chunks'] == 1675
    folder = ROOT / 'qa_tests'
    folder.mkdir(parents=True, exist_ok=True)
    report = []
    for index, (kind, question, terms, relevant_pages) in enumerate(QUESTIONS, 1):
        context_result = call_flow(api, question, 'parser-h3mx9', f'sysarch-v3-context-{index}')
        save_json_atomic(folder / f'{index}-context.json', context_result)
        context = context_text(context_result)
        assert context and '原PDF第' in context
        assert not any(term in context for term in ['文老师', '淘宝搜索', '宝搜索'])
        sources = {page for start, end in re.findall(r'原PDF第(\d+)(?:～(\d+))?页', context)
                   for page in range(int(start), int(end or start) + 1)}
        assert sources & relevant_pages, f'Relevant page missing for {kind}: {sources}'
        answer_result = call_flow(api, question, 'ChatOutput-QRg8s', f'sysarch-v3-answer-{index}')
        save_json_atomic(folder / f'{index}-answer.json', answer_result)
        answer = answer_text(answer_result)
        assert answer and not re.search(r'</?think\b', answer, re.I)
        assert all(term in answer for term in terms), f'Answer missing expected concept: {kind}'
        assert '原PDF第' in answer and '[片段' in answer, f'Answer missing citation: {kind}'
        report.append({'type': kind, 'question': question, 'sources': sorted(sources),
                       'answer': answer, 'passed': True})
        save_json_atomic(folder / 'report.json', report)
        print('QA_PASS', kind, sorted(sources), flush=True)
    save_json_atomic(folder / 'verification.json',
                     {'complete': True, 'passed': len(report), 'knowledge_base': 'SysArchTutorRAGv3'})
    print('V3_QA_COMPLETE', len(report), flush=True)


if __name__ == '__main__':
    verify()
