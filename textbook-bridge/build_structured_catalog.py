"""Index original table rows and formula locations without inventing missing math."""
import hashlib,json,re
from pathlib import Path
from structured import ROOT, BOOK_SHA, DIRECTORY, CATALOG, table_blocks, formula_lines,continuation_title

def main():
 mapping=json.loads((ROOT/'output/sysarch-page-citations/page-map.json').read_text(encoding='utf-8'))
 chunks=json.loads((ROOT/'output/sysarch-fullbook-v3-watermark/final_chunks.json').read_text(encoding='utf-8'))
 chapters={}
 for c in chunks:
  m=c['metadata']
  if m.get('source_sha256')!=BOOK_SHA or m.get('section_type')!='body':continue
  for p in str(m['pdf_pages']).split(','):
   if p.isdigit():chapters[int(p)]=m.get('chapter','')
 records=[];previous=None;stats={'tablePages':0,'formulaPages':0,'tables':0,'undecodedFormulaPages':0}
 for p in range(18,728):
  original=json.loads((ROOT/f'output/sysarch-fullbook-v2/pages/page_{p:04d}.json').read_text(encoding='utf-8'))
  if original['source_sha256']!=BOOK_SHA or original['page']!=p:raise ValueError('Page source mismatch')
  text=(ROOT/f'output/sysarch-fullbook-v3-watermark/pages/page_{p:04d}.md').read_text(encoding='utf-8')
  tables=table_blocks(text);lines=formula_lines(text)
  missing=any(b['label']=='formula' for b in original['blocks']) or '<!-- formula-not-decoded -->' in text
  kinds=(['table'] if tables else [])+(['formula'] if lines or missing else [])
  if not kinds:continue
  stats['tablePages']+=bool(tables);stats['formulaPages']+=bool(lines or missing);stats['tables']+=len(tables);stats['undecodedFormulaPages']+=missing
  titles=re.findall(r'^\s*(表\s*\d+\s*[-－—]\s*\d+[^\n]{0,100})',text,re.M)
  continuation=continuation_title(text,tables,previous,p)
  if continuation:titles.insert(0,continuation)
  if tables and titles:previous={'page':p,'title':titles[-1].split('（续表')[0],'header':tables[-1].splitlines()[0]}
  else:previous=None
  headings=re.findall(r'^#{1,6}\s+([^\n]+)',text,re.M)
  kind='formula' if 'formula' in kinds else 'table'
  caption=('；'.join(titles) if titles else ('教材公式原页' if kind=='formula' else '教材表格原页')+' · '+' / '.join(headings[:3]))[:500]
  if not caption.strip():caption=f'教材结构内容原页 · PDF第{p}页'
  book=mapping['pages'][str(p)].get('book_page')
  label=f'教材第{book}页（PDF第{p}页）' if book is not None else f'PDF第{p}页（无印刷页码）'
  context=('原页结构内容（OCR未解码处必须对照原页，不得补造）：\n'+'\n\n'.join(tables+lines)+'\n\n相关正文：\n'+text)[:12000]
  records.append({'id':hashlib.sha256(f'{BOOK_SHA}:structured:{p}'.encode()).hexdigest(),'kind':kind,'kinds':kinds,'caption':caption,'pdfPage':p,'bbox':[0,0,1,1],'pageSize':[1,1],'context':context,'label':label,'chapter':chapters.get(p,''),'formulaUndecoded':missing})
 # Physical page sizes come from the verified original PDF, not OCR geometry.
 import pypdfium2 as pdfium
 from pages import PageRenderer
 renderer=PageRenderer()
 with pdfium.PdfDocument(str(renderer.path)) as doc:
  for r in records:
   page=doc[r['pdfPage']-1];r['pageSize']=list(page.get_size());page.close()
 DIRECTORY.mkdir(parents=True,exist_ok=True)
 raw=json.dumps({'bookSha':BOOK_SHA,'figures':records,'statistics':stats},ensure_ascii=False,indent=2)
 temp=CATALOG.with_suffix('.tmp.json');temp.write_text(raw,encoding='utf-8');temp.replace(CATALOG)
 print(json.dumps({'indexedPages':len(records),**stats,'catalog':str(CATALOG)},ensure_ascii=False))

if __name__=='__main__':main()
