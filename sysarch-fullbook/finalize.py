"""Run only after full ingestion and final QA have passed."""
import copy
import json
from pathlib import Path
from core import save_json_atomic
from langflow_api import LangflowAPI
from parse_book import ROOT
from setup_langflow import backup_vectors
from review_quality import review


def finalize():
    progress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
    assert progress['state']=='complete' and progress['next_page']==729
    report=json.loads((ROOT/'qa_tests'/'final'/'report.json').read_text(encoding='utf-8'))
    qa_verification=json.loads((ROOT/'qa_tests'/'final'/'verification.json').read_text(encoding='utf-8'))
    assert qa_verification['complete'] and len(report)==qa_verification['test_count']
    assert len(report)>=7 and all(r['passed'] for r in report)
    quality=review()
    manual=json.loads((ROOT/'manual_quality_review.json').read_text(encoding='utf-8'))
    unresolved=[r['page'] for r in quality['flagged_pages'] if r['section']=='body'
                and r['page'] not in manual['body_sparse_pages_reviewed']]
    unresolved.extend(p for p in quality['body_pages_under_300_characters']
                      if p not in manual['body_sparse_pages_reviewed'])
    assert not unresolved, f'Flagged body pages need original-PDF review: {unresolved}'
    api=LangflowAPI()
    setup=json.loads((ROOT/'langflow_setup.json').read_text(encoding='utf-8'))
    # Re-submit one existing cover chunk: duplicate rejection preserves the corpus,
    # while the stock component refreshes cached UI counts after pilot cleanup.
    refresh=api.run_ingest(setup['flow_id'],ROOT/'batches'/'pages_0728_0728.json')
    save_json_atomic(ROOT/'statistics_refresh.run.json',refresh)
    assert api.call('/knowledge_bases/SysArchTutorRAGv2')['chunks']==progress['verified_chunks']
    v1=api.call('/knowledge_bases/SysArchTutorRAGv1')
    old=json.loads((ROOT/'backups'/'SysArchTutorRAGv1-vectors.json').read_text(encoding='utf-8'))
    assert v1['chunks']==len(old['ids']), 'V1 chunk count changed'
    fid='2e38f267-52d8-484f-bc4a-81ad7a2e3436'
    flow=api.call('/flows/'+fid)
    original_data=copy.deepcopy(flow['data'])
    switch_backup=ROOT/'backups'/'教材检索与备考问答-before-production-switch.json'
    if not switch_backup.exists():
        save_json_atomic(switch_backup,flow)
    node=next(n for n in flow['data']['nodes'] if n['id']=='Knowledge-Y8gm2')
    template=node['data']['node']['template']
    template['knowledge_base']['value']='SysArchTutorRAGv2'
    template['metadata_filter']['value']=json.dumps({'section_type':'body'})
    if isinstance(template['knowledge_base'].get('options'),list):
        options=template['knowledge_base']['options']
        if options and all(isinstance(v,str) for v in options) and 'SysArchTutorRAGv2' not in options:
            options.append('SysArchTutorRAGv2')
    assert api.call('/flows/'+fid)['data']==original_data, 'Concurrent flow edit detected'
    api.call('/flows/'+fid,{'data':flow['data']},'PATCH')
    saved=api.call('/flows/'+fid)
    actual=next(n for n in saved['data']['nodes'] if n['id']=='Knowledge-Y8gm2')['data']['node']['template']
    assert actual['knowledge_base']['value']=='SysArchTutorRAGv2'
    assert json.loads(actual['metadata_filter']['value'])=={'section_type':'body'}
    save_json_atomic(ROOT/'教材检索与备考问答-正式版.json',saved)
    for flow_id in ['35d77167-24a6-4876-8c2d-0786a32ca259',setup['flow_id']]:
        saved_flow=api.call('/flows/'+flow_id)
        if flow_id==setup['flow_id']:
            original_aux=copy.deepcopy(saved_flow['data'])
            reader=next(n for n in saved_flow['data']['nodes'] if n['id']=='FullBookBatchReader-SysArch')
            reader['data']['node']['template']['batch_file']['value']=str(ROOT/'batches'/'pages_0018_0027.json')
            assert api.call('/flows/'+flow_id)['data']==original_aux, 'Concurrent batch-flow edit detected'
            api.call('/flows/'+flow_id,{'data':saved_flow['data']},'PATCH')
            saved_flow=api.call('/flows/'+flow_id)
        save_json_atomic(ROOT/(saved_flow['name']+'-完成后.json'),saved_flow)
    kb=backup_vectors(api,'SysArchTutorRAGv2',ROOT/'backups')
    assert kb['chunks']==progress['verified_chunks']
    save_json_atomic(ROOT/'final_chunks.json',api.chunks('SysArchTutorRAGv2'))
    result={'ingestion':progress['state'],'pages':728,'body_pages':[18,727],
            'chunks':kb['chunks'],'v1_chunks_preserved':v1['chunks'],'qa_tests_passed':len(report),
            'qa_knowledge_base':'SysArchTutorRAGv2','qa_filter':{'section_type':'body'},
            'vector_backup_restored_and_verified':True,'quality':quality}
    save_json_atomic(ROOT/'completion.json',result)
    text=f'''# 全书入库完成记录

原文件：系统架构设计师教程第二版(90M)压缩版！.pdf

- 原PDF 728个物理页全部有逐页解析记录；第18～727页为正文，第1～17页为前置内容，第728页为封底。
- 正式知识库：SysArchTutorRAGv2，共{kb['chunks']}个分片；每个分片正文、稳定ID及物理页码均已核对入库。
- 已有「教材检索与备考问答」已切换到V2，默认只检索正文；模型沿用MiniMax-M3。
- {len(report)}项实际问答验证通过，核对了检索来源与引用页码，聊天结果未出现think标签。
- 原V1保留{v1['chunks']}个分片；V1和V2均已导出完整向量，并在独立目录实际恢复验证正文、元数据和向量。
- 处理使用Docling standard、RapidOCR中文模型、700字符块大小和100字符重叠；Markdown和入库分片均已缓存，可按进度恢复。

## 保存位置

- 备份：backups/，包括流程JSON、知识库配置、文本、元数据、完整向量及恢复验证。
- 逐页正文：pages/page_XXXX.md；原始输出：pages/page_XXXX.raw.md。
- 已提交分片：batches/；确认进度：progress.json。
- 问答记录：qa_tests/final/report.md，原始检索及输出也在该目录。
- 操作脚本和恢复说明：F:/daily/sysarch-fullbook/README.md。

## 质量与后续工作

检查记录见quality_review.json和人工复查记录。覆盖与结构核对不能保证所有OCR字符正确，专业词、数字和复杂表格仍可依据原页复核。

第9章标题的元数据已对照原PDF第320页修正为“软件可靠性基础知识”；第17章重复的编号已对照第614页修正。保留原始OCR文件、修正记录及原图证据。少数章末页仍包含扫描水印，具体页号列在quality_review.json。

已保存{quality['saved_figure_files']}个图像裁剪文件。图像及识别出的文字已保留；图示关系、公式语义和图像描述仍需专项核对，不能视为已完成图示理解。
'''
    (ROOT/'完成记录.md').write_text(text,encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='quality'},ensure_ascii=False))


if __name__=='__main__':
    finalize()
