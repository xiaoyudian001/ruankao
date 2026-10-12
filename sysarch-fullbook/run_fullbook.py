import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from core import make_chunks, save_json_atomic
from parse_book import ROOT, SOURCE, source_identity, parse_batch, load_converter
from langflow_api import LangflowAPI

def segments_for_pages(records,chapter=''):
    segments=[]
    for record in records:
        for part in re.split(r'\n\n+',record['markdown']):
            match=re.match(r'^#{1,6}\s*(第[0-9零一二三四五六七八九十百]+章[^\n]*)',part.strip())
            if match:
                chapter=match.group(1)
            if part.strip():
                segments.append({'page':record['page'],'text':part,'chapter':chapter})
    return segments,chapter

def verify_rows(api,rows):
    stored={c['metadata'].get('chunk_id'):c for c in api.chunks('SysArchTutorRAGv2',[r['chunk_id'] for r in rows])}
    for row in rows:
        assert row['chunk_id'] in stored, 'Stored chunk ID missing: '+row['chunk_id']
        actual=stored[row['chunk_id']]
        assert actual['content']==row['text'], 'Stored text differs'
        assert actual['metadata']['pdf_page_start']==str(row['pdf_page_start'])
        assert actual['metadata']['pdf_page_end']==str(row['pdf_page_end'])
        assert actual['metadata']['source_sha256']==row['source_sha256']
    return stored

def submit(api,setup,path,rows):
    if not rows:
        return 0
    last=None
    for attempt in range(3):
        try:
            result=api.run_ingest(setup['flow_id'],path)
            save_json_atomic(path.with_suffix('.run.json'),result)
            verify_rows(api,rows)
            return len(rows)
        except Exception as error:
            last=error
            save_json_atomic(path.with_suffix('.error.json'),{'attempt':attempt+1,'error':str(error)})
            print('INGEST_RETRY',path.name,attempt+1,str(error)[:400],flush=True)
            if attempt<2:
                time.sleep(3)
    raise last

def pilot():
    identity=source_identity()
    setup=json.loads((ROOT/'langflow_setup.json').read_text(encoding='utf-8'))
    api=LangflowAPI()
    records=parse_batch(18,30)
    assert all(r['chinese_characters']>300 for r in records), 'Pilot contains an unexpected sparse page'
    terms=['8000','84%','189%','事件队列','事件通道','事件处理器','框架模型','微核架构']
    text=''.join(r['markdown'] for r in records)
    assert all(t in text for t in terms)
    segments,chapter=segments_for_pages(records)
    rows,state=make_chunks({},segments,identity['sha256'],identity['filename'],'body',final=False)
    path=ROOT/'pilot'/'pages_0018_0030.json'
    save_json_atomic(path,rows)
    submit(api,setup,path,rows)
    count=len(api.chunks('SysArchTutorRAGv2'))
    submit(api,setup,path,rows)
    assert len(api.chunks('SysArchTutorRAGv2'))==count, 'Retry created duplicates'
    assert any(r['pdf_page_start']<r['pdf_page_end'] for r in rows)
    save_json_atomic(ROOT/'pilot'/'verification.json',{'pages':13,'chunks':count,'metadata_verified':True,
                                                    'repeat_did_not_add_chunks':True,'known_terms_present':True,
                                                    'cross_page_chunks_present':True})
    print('PILOT_PASS',count,'chunks; metadata and retry verified',flush=True)

def run_fullbook():
    identity=source_identity()
    setup=json.loads((ROOT/'langflow_setup.json').read_text(encoding='utf-8'))
    api=LangflowAPI()
    progress_path=ROOT/'progress.json'
    progress=json.loads(progress_path.read_text(encoding='utf-8')) if progress_path.exists() else {
        'source_sha256':identity['sha256'],'total_pages':identity['pages'],'next_page':1,
        'chunk_state':{},'chapter':'','completed_batches':[],'expected_chunk_ids':[],
        'state':'running','started_at':time.strftime('%Y-%m-%d %H:%M:%S')}
    assert progress['source_sha256']==identity['sha256']
    converter=None
    while progress['next_page']<=identity['pages']:
        start=progress['next_page']
        section='front_matter' if start<=17 else ('back_matter' if start==identity['pages'] else 'body')
        last_in_section=17 if start<=17 else (identity['pages'] if section=='back_matter' else identity['pages']-1)
        end=min(start+9,last_in_section)
        began=time.monotonic()
        pending_path=ROOT/'batches'/f'pages_{start:04}_{end:04}.json'
        checkpoint=pending_path.with_suffix('.checkpoint.json')
        if checkpoint.exists() and pending_path.exists():
            rows=json.loads(pending_path.read_text(encoding='utf-8'))
            next_state=json.loads(checkpoint.read_text(encoding='utf-8'))
            assert next_state['start']==start
        else:
            cache_paths=[ROOT/'pages'/f'page_{p:04}.json' for p in range(start,end+1)]
            if not all(p.exists() for p in cache_paths) and converter is None:
                converter=load_converter()
            records=parse_batch(start,end,converter)
            segments,chapter=segments_for_pages(records,progress['chapter'])
            rows,state=make_chunks(progress['chunk_state'],segments,identity['sha256'],identity['filename'],section,
                                   final=end==last_in_section)
            for row in rows:
                row['batch_id']=f'pages{start:04}to{end:04}'
            save_json_atomic(pending_path,rows)
            next_state={'start':start,'next_page':end+1,'chunk_state':state,'chapter':chapter if end!=17 else '',
                        'review_flags':{str(r['page']):r['review_flags'] for r in records if r['review_flags']}}
            save_json_atomic(checkpoint,next_state)
        submit(api,setup,pending_path,rows)
        progress.update({'next_page':next_state['next_page'],'chunk_state':next_state['chunk_state'],
                         'chapter':next_state['chapter'],'state':'running','updated_at':time.strftime('%Y-%m-%d %H:%M:%S')})
        progress['completed_batches'].append({'start':start,'end':end,'rows':len(rows),
                                             'seconds':round(time.monotonic()-began,1),'review_flags':next_state['review_flags']})
        progress['expected_chunk_ids'].extend(r['chunk_id'] for r in rows)
        save_json_atomic(progress_path,progress)
        print(json.dumps({'completed_pages':end,'total_pages':identity['pages'],
                          'generated_chunks':len(set(progress['expected_chunk_ids'])),
                          'batch_seconds':round(time.monotonic()-began,1),'review_flags':next_state['review_flags']},
                         ensure_ascii=False),flush=True)
    stored=api.chunks('SysArchTutorRAGv2')
    actual={c['metadata'].get('chunk_id') for c in stored}
    expected=set(progress['expected_chunk_ids'])
    assert actual==expected, f'Unexpected/missing chunks: extra={len(actual-expected)} missing={len(expected-actual)}'
    pages={r for b in progress['completed_batches'] for r in range(b['start'],b['end']+1)}
    assert pages==set(range(1,identity['pages']+1))
    progress.update({'state':'complete','verified_chunks':len(actual),'finished_at':time.strftime('%Y-%m-%d %H:%M:%S')})
    save_json_atomic(progress_path,progress)
    save_json_atomic(ROOT/'final_chunks.json',stored)
    print('FULLBOOK_INGEST_COMPLETE',len(pages),'pages',len(actual),'chunks',flush=True)

if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('--pilot',action='store_true')
    value=args.parse_args()
    pilot() if value.pilot else run_fullbook()
