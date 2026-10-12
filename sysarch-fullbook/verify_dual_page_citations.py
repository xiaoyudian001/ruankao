import json
import re
from core import save_json_atomic
from printed_page_mapping import ROOT
from langflow_api import LangflowAPI
from verify_qa import answer_text, context_text

FLOW='2e38f267-52d8-484f-bc4a-81ad7a2e3436'

def run(api, question, component, session):
    # No KB/citation tweaks: verify the saved default flow itself.
    return api.call('/run/session/'+FLOW,{'input_request':{
        'input_value':question,'input_type':'chat','output_type':'chat',
        'output_component':component,'session_id':session,
        'tweaks':{'ChatInput-z2rit':{'should_store_message':False},
                  'ChatOutput-QRg8s':{'should_store_message':False}}}},'POST',timeout=180)

def verify():
    api=LangflowAPI()
    assert api.call('/knowledge_bases/SysArchTutorRAGv3')['chunks']==1675
    tests=[('MTTR','依据教材，MTTR 的定义是什么？降低 MTTR 为什么有助于提高网络高可用性？'),
           ('跨页检索','依据教材，事件驱动架构由哪四个部分组成？各自的作用是什么？')]
    report=[]
    for index,(kind,question) in enumerate(tests,1):
        context_result=run(api,question,'parser-h3mx9','dual-pages-context-'+str(index))
        save_json_atomic(ROOT/'qa_tests'/f'{index}-context.json',context_result)
        context=context_text(context_result)
        assert '教材第' in context and 'PDF第' in context
        if kind=='MTTR':
            assert '教材第308页（PDF第323页）' in context
        hints={int(m.group(1)):m.group(2).split('；')[1] for m in re.finditer(
            r'\[片段(\d+)\]\s*来源：([^\n]+)',context)}
        result=run(api,question,'ChatOutput-QRg8s','dual-pages-answer-'+str(index))
        save_json_atomic(ROOT/'qa_tests'/f'{index}-answer.json',result)
        answer=answer_text(result)
        assert answer and not re.search(r'</?think\b',answer,re.I)
        assert '教材第' in answer and 'PDF第' in answer
        citations=[]
        for m in re.finditer(r'\[片段(\d+)[，,]\s*([^\]\n]+)\]',answer):
            rank=int(m.group(1));label=m.group(2)
            # Every cited range must exactly equal that retrieved fragment's source label.
            assert rank in hints,(rank,hints)
            expected=hints[rank].replace('（物理页）','')
            assert expected==label,(label,expected)
            citations.append({'fragment':rank,'label':label})
        assert citations,answer
        if kind=='MTTR': assert any(c['label']=='教材第308页（PDF第323页）' for c in citations)
        report.append({'type':kind,'question':question,'context_sources':hints,
                       'answer':answer,'citations':citations,'passed':True})
        save_json_atomic(ROOT/'qa_tests'/'report.json',report)
        print('QA_PASS',kind,json.dumps(citations,ensure_ascii=False),flush=True)
    (ROOT/'qa_tests'/'report.md').write_text('# 双页码问答验证\n\n'+'\n\n'.join(
        f'## {r["type"]}\n\n{r["question"]}\n\n{r["answer"]}' for r in report),encoding='utf-8')
    save_json_atomic(ROOT/'qa-verification.json',{'default_saved_flow_verified':True,
        'questions':len(report),'citations_match_retrieved_sources':True,
        'think_hidden':True,'mttr_book_308_pdf_323_verified':True})
    print('ALL_DUAL_CITATION_TESTS_PASSED',flush=True)

if __name__=='__main__': verify()
