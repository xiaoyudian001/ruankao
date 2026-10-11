"""Associate original crops with reviewed page labels and cleaned page text."""
import hashlib,json
from pathlib import Path
import pypdfium2 as pdfium
from pages import PageRenderer
from figures import ROOT,ASSETS,BOOK_SHA,CATALOG
def main():
 renderer=PageRenderer();mapping=json.loads((ROOT/'output/sysarch-page-citations/page-map.json').read_text(encoding='utf-8'))
 chunks=json.loads((ROOT/'output/sysarch-fullbook-v3-watermark/final_chunks.json').read_text(encoding='utf-8'))
 context={};chapters={}
 for c in chunks:
  m=c['metadata']
  if m.get('section_type')!='body' or m.get('source_sha256')!=BOOK_SHA:continue
  for p in str(m.get('pdf_pages','')).split(','):
   if not p.isdigit():continue
   page=int(p);context.setdefault(page,[]).append(c['content']);chapters[page]=m.get('chapter','')
 inventory=json.loads((ROOT/'output/sysarch-fullbook-v2/figure_inventory.json').read_text(encoding='utf-8'));figures=[];skipped=0
 with pdfium.PdfDocument(str(renderer.path)) as doc:
  for r in inventory:
   page=r['pdf_page'];caption=' '.join(r.get('captions',[])).strip();path=Path(r.get('path','')).resolve()
   if not 18<=page<=727 or r.get('kind')!='figure' or r.get('area_ratio',0)<.02 or not caption or not path.is_relative_to(ASSETS) or not path.is_file():skipped+=1;continue
   original=doc[page-1];w,h=original.get_size();original.close();b=r['bbox'];box=[b['l']/w,b['t']/h,(b['r']-b['l'])/w,(b['b']-b['t'])/h]
   if any(v<0 or v>1 for v in box) or box[0]+box[2]>1.001 or box[1]+box[3]>1.001:skipped+=1;continue
   ident=hashlib.sha256((BOOK_SHA+f':{page}:{r["picture_index"]}').encode()).hexdigest();book=mapping['pages'][str(page)].get('book_page')
   label=(f'教材第{book}页（PDF第{page}页）' if book is not None else f'PDF第{page}页（本页无印刷页码）')
   cleanpage=ROOT/f'output/sysarch-fullbook-v3-watermark/pages/page_{page:04d}.md'
   text=cleanpage.read_text(encoding='utf-8') if cleanpage.exists() else '\n\n'.join(dict.fromkeys(context.get(page,[])))
   figures.append({'id':ident,'caption':caption,'pdfPage':page,'bbox':box,'pageSize':[w,h],'path':str(path),'imageSha':hashlib.sha256(path.read_bytes()).hexdigest(),'context':('原书图题：'+caption+'\n\n相关页正文：\n'+text)[:12000],'label':label,'chapter':chapters.get(page,'')})
 CATALOG.parent.mkdir(exist_ok=True);CATALOG.write_text(json.dumps({'bookSha':BOOK_SHA,'figures':figures,'skipped':skipped},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'indexed':len(figures),'skipped':skipped,'catalog':str(CATALOG)},ensure_ascii=False))
if __name__=='__main__':main()
