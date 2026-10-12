import hashlib
import json
import os
import re
from pathlib import Path

VERSION = 'sysarch-v2-700-100-1'

def clean_text(text):
    text = text.replace('\r\n','\n').replace('\r','\n').replace('\u200b','')
    text = re.sub(r'(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])\n(?=[\u4e00-\u9fff])', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def make_chunks(state, segments, source_sha, source_file, section, final=False):
    state = json.loads(json.dumps(state))
    text = state.get('text','')
    pages = state.get('pages',[])
    chapters = state.get('chapters',[])
    offset = state.get('offset',0)
    overlap = state.get('overlap',0)
    rows = []

    def emit(end):
        raw = text[:end]
        left = len(raw)-len(raw.lstrip())
        right = len(raw.rstrip())
        body = raw[left:right]
        if not body:
            return
        used_pages = sorted({pages[i] for i in range(left,right) if not raw[i].isspace()})
        used_chapters = list(dict.fromkeys(chapters[i] for i in range(left,right) if chapters[i]))
        chunk_id=stable_chunk_id(source_sha,section,offset+left,used_pages,body)
        rows.append({'text':body, 'source_file':source_file, 'source_sha256':source_sha,
                     'pdf_page_start':min(used_pages), 'pdf_page_end':max(used_pages),
                     'pdf_pages':','.join(map(str,used_pages)), 'chapter':' / '.join(used_chapters),
                     'section_type':section, 'chunk_id':chunk_id,
                     'source_metadata':json.dumps({'section_type':section,'chunk_id':chunk_id},ensure_ascii=False),
                     'processing_version':VERSION})

    for segment in segments:
        body = clean_text(segment['text'])
        body = re.sub(r'<!--\s*image\s*-->', '', body).strip()
        if not body:
            continue
        joiner = ''
        if text:
            continuation = (pages[-1] != segment['page'] and
                            bool(re.search(r'[\u4e00-\u9fff]$',text)) and
                            bool(re.match(r'[\u4e00-\u9fff]',body)) and
                            chapters[-1] == segment.get('chapter',''))
            joiner = '' if continuation else '\n\n'
        addition = joiner + body
        text += addition
        pages.extend([segment['page']]*len(addition))
        chapters.extend([segment.get('chapter','')]*len(addition))
        while len(text)>700:
            end=700
            boundary=text.rfind('\n\n',350,701)
            if boundary>=350:
                end=min(boundary+2,700)
            else:
                stops=list(re.finditer(r'[。！？；]\s*',text[350:700]))
                if stops:
                    end=350+stops[-1].end()
            emit(end)
            advance=end-100
            text,pages,chapters=text[advance:],pages[advance:],chapters[advance:]
            offset+=advance
            overlap=100
    if final:
        if len(text)>overlap:
            emit(len(text))
        offset+=len(text)
        text,pages,chapters='',[],[]
        overlap=0
    return rows, {'text':text,'pages':pages,'chapters':chapters,'offset':offset,'overlap':overlap}

def stable_chunk_id(source_sha, section, offset, pages, text):
    payload=[VERSION,source_sha,section,offset,pages,text]
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def save_json_atomic(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
