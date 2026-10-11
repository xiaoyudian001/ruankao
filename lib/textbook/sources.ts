import {checkedFigures,type TextbookFigure} from './figures.ts';
export const BOOK_SHA = 'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9';
export type SourceReference = {rank:number;bookSha:string;chunkId:string;content:string;pdfPages:number[];label:string;chapter:string;figures?:TextbookFigure[]};
export type SourceSummary = Omit<SourceReference,'content'|'chunkId'|'bookSha'>;

export function references(value:unknown):SourceReference[] {
  if(value==null)return [];
  if(!Array.isArray(value)||value.length>10)throw new Error('Invalid source references');
  const ranks=new Set<number>();const figureIds=new Set<string>();
  return value.map(item=>{
    if(!item||typeof item!=='object')throw new Error('Invalid source reference');
    const r=item as Record<string,unknown>;
    if(!Number.isInteger(r.rank)||Number(r.rank)<1||Number(r.rank)>10||ranks.has(Number(r.rank))||r.bookSha!==BOOK_SHA)throw new Error('Invalid source identity');
    if(typeof r.chunkId!=='string'||!/^[a-f0-9]{64}$/.test(r.chunkId))throw new Error('Invalid chunk');
    if(typeof r.content!=='string'||!r.content.trim()||r.content.length>12000||typeof r.label!=='string'||r.label.length>500||typeof r.chapter!=='string'||r.chapter.length>200)throw new Error('Invalid source text');
    if(!Array.isArray(r.pdfPages)||!r.pdfPages.length||r.pdfPages.length>6||!r.pdfPages.every((p,i)=>Number.isInteger(p)&&p>=1&&p<=728&&(i===0||p===Number((r.pdfPages as number[])[i-1])+1)))throw new Error('Invalid source pages');
    ranks.add(Number(r.rank));
    const figures=checkedFigures(r.figures,r.pdfPages as number[]);
    for(const figure of figures){if(figureIds.has(figure.id)||figureIds.size>=2)throw new Error('Too many or duplicate figures');figureIds.add(figure.id);}
    return {rank:Number(r.rank),bookSha:BOOK_SHA,chunkId:r.chunkId,content:r.content,pdfPages:r.pdfPages as number[],label:r.label,chapter:r.chapter,...(figures.length?{figures}:{})};
  });
}
export function storedReferences(value:unknown):SourceReference[]{
  try{return references(typeof value==='string'?JSON.parse(value):value);}catch{return [];}
}
export function sourceSummaries(value:unknown):SourceSummary[]{
  return storedReferences(value).map(({rank,pdfPages,label,chapter,figures})=>({rank,pdfPages,label,chapter,...(figures?.length?{figures}:{})}));
}
export function selectedReference(value:unknown,rank:unknown,page:unknown):SourceReference|null{
  if(!Number.isInteger(rank)||!Number.isInteger(page))return null;
  return storedReferences(value).find(r=>r.rank===rank&&r.pdfPages.includes(Number(page)))??null;
}
export const PAGE_CLAIM_SQL=`UPDATE textbook_pages SET status='running',lease=?,updated_at=?
WHERE page=(SELECT page FROM textbook_pages WHERE status='queued' ORDER BY created_at,page LIMIT 1)
AND status='queued' AND NOT EXISTS (SELECT 1 FROM textbook_pages WHERE status='running')
RETURNING page,lease`;
export const PAGE_FINISH_SQL=`UPDATE textbook_pages SET status='ready',file_key=?,error=NULL,lease=NULL,updated_at=?
WHERE page=? AND status='running' AND lease=? AND updated_at>=? RETURNING page`;
