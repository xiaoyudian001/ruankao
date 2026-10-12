import json
from collections import Counter
from pathlib import Path
from core import save_json_atomic
from printed_page_mapping import ROOT
from citation_format import source_hint

def verify():
    flow_before=json.loads((ROOT/'backups'/'教材检索与备考问答-before-dual-pages.json').read_text(encoding='utf-8'))
    flow_after=json.loads((ROOT/'backups'/'教材检索与备考问答-after-dual-pages.json').read_text(encoding='utf-8'))
    before=flow_before['data'];after=flow_after['data']
    nodes={n['id']:n for n in after['nodes']}
    changes=[]
    for node in before['nodes']:
        current=nodes[node['id']]
        for field in node['data']['node']['template']:
            a=node['data']['node']['template'][field];b=current['data']['node']['template'][field]
            if a!=b: changes.append((node['id'],field))
    assert set(changes)=={('parser-h3mx9','code'),('Prompt Template-fzcHC','template')},changes
    assert before['edges']==after['edges'] and before['viewport']==after['viewport']
    fields={'book_pages','book_page_start','book_page_end','book_page_mapping_status','page_mapping_version'}
    checked=0
    for old_file in (ROOT/'backups'/'cached-files').rglob('*.json'):
        relative=old_file.relative_to(ROOT/'backups'/'cached-files')
        new_file=Path(r'F:\daily\output')/relative
        old=json.loads(old_file.read_text(encoding='utf-8'));new=json.loads(new_file.read_text(encoding='utf-8'))
        assert len(old)==len(new)
        for a,b in zip(old,new):
            if 'metadata' in a:
                actual={**b,'metadata':{k:v for k,v in b['metadata'].items() if k not in fields}}
            else: actual={k:v for k,v in b.items() if k not in fields}
            assert actual==a,'Existing cached content/metadata changed'
        checked+=1
    chunks=json.loads(Path(r'F:\daily\output\sysarch-fullbook-v3-watermark\final_chunks.json').read_text(encoding='utf-8'))
    labels=[]
    for row in chunks:
        meta=row['metadata'];label=source_hint(meta)
        assert label
        if meta['book_page_mapping_status']=='complete': assert '教材第' in label
        else: assert '原PDF第' in label
        if meta['pdf_pages']=='323' and 'MTTR' in row['content']:
            assert '教材第308页（PDF第323页）' in label
            labels.append(label)
    assert labels
    save_json_atomic(ROOT/'artifact-verification.json',{
        'flow_fields_changed':changes,'edges_positions_model_kb_unchanged':True,
        'cached_files_checked':checked,'all_existing_cached_text_and_metadata_preserved':True,
        'all_chunk_citation_labels_validated':len(chunks),'mttr_source_labels':labels})
    print('ARTIFACTS_VERIFIED',checked,'cached files;',len(chunks),'citation labels; 2 flow fields changed')

if __name__=='__main__': verify()
