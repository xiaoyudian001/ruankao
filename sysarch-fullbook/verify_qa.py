import argparse
import json
import re
import time
from core import save_json_atomic
from langflow_api import LangflowAPI
from parse_book import ROOT

TESTS=[
    ('定义','依据教材，什么是微核架构？内核和插件分别承担什么？',['微核','插件','最小']),
    ('列举','依据教材，事件驱动架构由哪四个部分组成？各自作用是什么？',['事件队列','分发器','事件通道','事件处理器']),
    ('比较','依据教材，结构模型与框架模型有什么区别？',['结构模型','框架模型','整体','细节']),
    ('无答案','依据教材，NebulaGhost2099量子路由器的默认管理端口是什么？请给出教材明确记载的数值。',[]),
]

def context_text(result):
    for group in result.get('outputs',[]):
        for output in group.get('outputs',[]):
            artifact=output.get('artifacts',{}).get('parsed_text',{})
            if isinstance(artifact.get('raw'),str):
                return artifact['raw']
    return ''

def answer_text(result):
    for group in result.get('outputs',[]):
        for output in group.get('outputs',[]):
            for message in output.get('results',{}).values():
                if isinstance(message,dict) and isinstance(message.get('text'),str):
                    return message['text']
    return ''

def verify(phase):
    api=LangflowAPI()
    folder=ROOT/'qa_tests'/phase
    folder.mkdir(parents=True,exist_ok=True)
    report=[]
    tests=list(TESTS)
    if phase=='final':
        tests.append(('数据库章节','依据教材，数据库三级模式分别是什么？外模式与内模式各描述什么？',
                      ['外模式','概念模式','内模式','存储']))
        tests.append(('云原生章节','依据教材，在云原生微服务设计中，可发现性和可交互性分别是什么？服务注册中心与远程调用协议各解决什么问题？',
                      ['注册中心','REST','调用']))
        tests.append(('论文写作章节','根据教材，系统架构设计师论文试题的三个考查目的是什么？请分别说明。',
                      ['实践经验','分析','表达']))
    for i,(kind,question,terms) in enumerate(tests,1):
        body={'input_request':{'input_value':question,'input_type':'chat','output_type':'any',
                               'output_component':'parser-h3mx9',
                               'tweaks':{'Knowledge-Y8gm2':{'knowledge_base':'SysArchTutorRAGv2',
                                                          'metadata_filter':json.dumps({'section_type':'body'})},
                                         'ChatInput-z2rit':{'should_store_message':False},
                                         'ChatOutput-QRg8s':{'should_store_message':False}},
                               'session_id':f'sysarch-v2-{phase}-{i}'}}
        context_result=api.call('/run/session/2e38f267-52d8-484f-bc4a-81ad7a2e3436',body,'POST',timeout=90)
        save_json_atomic(folder/f'{i}-context.json',context_result)
        context=context_text(context_result)
        assert context and ('原PDF第' in context), 'Source pages missing from retrieval formatter'
        pairs={}
        for match in re.finditer(r'\[片段(\d+)\]\s*来源：[^\n]*?原PDF第(\d+)(?:～(\d+))?页',context):
            pairs[int(match[1])]=(int(match[2]),int(match[3] or match[2]))
        body['input_request']['output_type']='chat'
        body['input_request']['output_component']='ChatOutput-QRg8s'
        began=time.monotonic()
        result=api.call('/run/session/2e38f267-52d8-484f-bc4a-81ad7a2e3436',body,'POST',timeout=180)
        save_json_atomic(folder/f'{i}-answer.json',result)
        answer=answer_text(result)
        assert answer and not re.search(r'</?think\b',answer,re.I)
        citations=[]
        if terms:
            assert all(term in answer for term in terms), 'Expected knowledge point missing'
            for match in re.finditer(r'\[片段(\d+)[^\]\n]*?原PDF第(\d+)(?:[～—–\-至](\d+))?页[^\]\n]*\]',answer):
                rank=int(match[1]); pages=(int(match[2]),int(match[3] or match[2]))
                assert rank in pairs and pages==pairs[rank], f'Incorrect citation {match[0]}; context={pairs}'
                citations.append({'fragment':rank,'pdf_page_start':pages[0],'pdf_page_end':pages[1]})
            assert citations,'Answer missing physical page citations in expected bracket format'
            minimum={'数据库章节':200,'云原生章节':400,'论文写作章节':700}.get(kind)
            if minimum is not None:
                assert any(c['pdf_page_end']>=minimum for c in citations), 'Expanded-corpus test did not cite its chapter area'
        else:
            assert any(term in answer for term in ['不足以','未提供','没有提供','没有记载','未记载','未找到']), 'Absent-answer test invented an answer'
            assert not re.search(r'默认.*端口.*(?:为|是)\s*\d+',answer), 'Invented default port'
        row={'type':kind,'question':question,'answer':answer,'seconds':round(time.monotonic()-began,1),
             'citations':citations,'passed':True}
        report.append(row)
        save_json_atomic(folder/'report.json',report)
        (folder/'report.md').write_text('# 正式库问答验证\n\n'+'\n\n'.join(
            f'## {r["type"]}\n\n{r["question"]}\n\n{r["answer"]}' for r in report),encoding='utf-8')
        print(json.dumps(row,ensure_ascii=False),flush=True)
    save_json_atomic(folder/'verification.json',{'complete':True,'test_count':len(tests),
                                                'types':[r['type'] for r in report]})
    print('QA_VERIFIED',phase,len(report),'tests',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',default='pilot')
    verify(parser.parse_args().phase)
