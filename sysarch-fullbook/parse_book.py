import argparse
import ast
import hashlib
import json
import os
import re
import sys
import textwrap
import time
from pathlib import Path

os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
from core import clean_text, save_json_atomic, VERSION

SOURCE=Path(r'F:\软考\系统架构设计师教程第二版(90M)压缩版！.pdf')
ROOT=Path(r'F:\daily\output\sysarch-fullbook-v2')
SAVED=Path(r'F:\daily\output\sysarch-rag-batch-021-030\saved_file.py')

def load_converter():
    tree=ast.parse(SAVED.read_text(encoding='utf-8'))
    child=next(n.value.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id=='child_script' for t in n.targets)
               and isinstance(n.value,ast.Call))
    inner=ast.parse(textwrap.dedent(child))
    selected=[n for n in inner.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))]
    namespace={}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'saved_docling_converter','exec'),namespace)
    status,formats,converter_cls,image_mode,strategy=namespace['try_imports']()
    converter=namespace['create_converter'](strategy,formats,converter_cls,'standard','rapidocr')
    options=converter.format_to_options[formats.PDF].pipeline_options
    assert options.do_ocr and options.ocr_options.kind=='rapidocr', 'OCR configuration failed; refusing silent fallback'
    return converter

def source_identity():
    manifest=ROOT/'source.json'
    if manifest.exists():
        value=json.loads(manifest.read_text(encoding='utf-8'))
        assert value['bytes']==SOURCE.stat().st_size and value['mtime_ns']==SOURCE.stat().st_mtime_ns
        return value
    from pypdf import PdfReader
    value={'path':str(SOURCE),'filename':SOURCE.name,'sha256':hashlib.file_digest(SOURCE.open('rb'),'sha256').hexdigest(),
           'bytes':SOURCE.stat().st_size,'mtime_ns':SOURCE.stat().st_mtime_ns,
           'pages':len(PdfReader(SOURCE).pages),'processing_version':VERSION}
    save_json_atomic(manifest,value)
    return value

def crop_pictures(doc,start,end):
    import pypdfium2 as pdfium
    from docling_core.types.doc import CoordOrigin
    pictures=[]
    with pdfium.PdfDocument(str(SOURCE)) as pdf:
        for index,picture in enumerate(doc.pictures):
            if not picture.prov:
                continue
            prov=picture.prov[0]
            page=prov.page_no
            assert start<=page<=end
            bbox=prov.bbox
            size=doc.pages[page].size
            box=bbox.to_top_left_origin(page_height=size.height)
            ratio=abs((box.r-box.l)*(box.b-box.t))/(size.width*size.height)
            row={'pdf_page':page,'picture_index':index,'bbox':box.model_dump(mode='json'),
                 'area_ratio':round(ratio,4),'kind':'page_image' if ratio>.9 else 'figure',
                 'text_description_status':'pending','captions':[]}
            for ref in picture.captions:
                item=ref.resolve(doc)
                if hasattr(item,'text'):
                    row['captions'].append(item.text)
            if ratio<=.9:
                page_obj=pdf[page-1]
                image=page_obj.render(scale=120/72).to_pil()
                bounds=(max(0,int(box.l*120/72)),max(0,int(box.t*120/72)),
                        min(image.width,int(box.r*120/72)),min(image.height,int(box.b*120/72)))
                if bounds[2]>bounds[0] and bounds[3]>bounds[1]:
                    path=ROOT/'figures'/f'page_{page:04}_figure_{index:03}.png'
                    path.parent.mkdir(parents=True,exist_ok=True)
                    image.crop(bounds).save(path)
                    row['path']=str(path)
                page_obj.close()
            pictures.append(row)
    return pictures

def parse_batch(start,end,converter=None):
    identity=source_identity()
    cache_paths=[ROOT/'pages'/f'page_{p:04}.json' for p in range(start,end+1)]
    if all(p.exists() for p in cache_paths):
        return [json.loads(p.read_text(encoding='utf-8')) for p in cache_paths]
    converter=converter or load_converter()
    if any(p.exists() for p in cache_paths):
        missing=[page for page,path in zip(range(start,end+1),cache_paths) if not path.exists()]
        first=last=missing[0]
        for page in missing[1:]+[end+2]:
            if page==last+1:
                last=page
            else:
                parse_batch(first,last,converter)
                first=last=page
        return [json.loads(p.read_text(encoding='utf-8')) for p in cache_paths]
    began=time.monotonic()
    result=converter.convert(SOURCE,page_range=(start,end))
    if str(result.status.value)!='success':
        raise RuntimeError(f'Docling failed batch {start}-{end}: {result.status}')
    doc=result.document
    assert set(doc.pages)==set(range(start,end+1)), f'Original page provenance mismatch: {list(doc.pages)}'
    pictures=crop_pictures(doc,start,end)
    records=[]
    for page,path in zip(range(start,end+1),cache_paths):
        raw=doc.export_to_markdown(page_no=page,traverse_pictures=True,escape_html=False,
                                   escape_underscores=False,image_placeholder='<!-- image -->')
        cleaned=clean_text(raw)
        blocks=[]
        for item,level in doc.iterate_items(traverse_pictures=True):
            if not getattr(item,'prov',None) or not any(p.page_no==page for p in item.prov):
                continue
            if hasattr(item,'text'):
                blocks.append({'label':str(item.label.value),'text':item.text,
                               'page_numbers':sorted({p.page_no for p in item.prov})})
        record={'page':page,'markdown':cleaned,'source_sha256':identity['sha256'],'processing_version':VERSION,
                'characters':len(cleaned),'chinese_characters':sum('\u4e00'<=c<='\u9fff' for c in cleaned),
                'blocks':blocks,'pictures':[pic for pic in pictures if pic['pdf_page']==page],
                'review_flags':[]}
        meaningful=re.sub(r'<!--.*?-->','',cleaned,flags=re.S).strip()
        if len(meaningful)<60:
            record['review_flags'].append('sparse_text_or_image_page')
        if '&amp;' in cleaned or '\ufffd' in cleaned:
            record['review_flags'].append('encoding_or_ocr_artifact')
        (ROOT/'pages').mkdir(parents=True,exist_ok=True)
        path.with_suffix('.raw.md').write_text(raw,encoding='utf-8')
        path.with_suffix('.md').write_text(cleaned,encoding='utf-8')
        save_json_atomic(path,record)
        records.append(record)
    save_json_atomic(ROOT/'parse_batches'/f'{start:04}-{end:04}.json',
                     {'start':start,'end':end,'seconds':round(time.monotonic()-began,1),
                      'page_count':len(records),'characters':sum(r['characters'] for r in records),
                      'pictures':len(pictures)})
    print(json.dumps({'parsed':f'{start}-{end}','seconds':round(time.monotonic()-began,1),
                      'characters':sum(r['characters'] for r in records)},ensure_ascii=False),flush=True)
    return records

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',type=int,default=18)
    parser.add_argument('--end',type=int,default=30)
    args=parser.parse_args()
    parse_batch(args.start,args.end)
