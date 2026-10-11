export type TextbookFigure={id:string;caption:string;pdfPage:number;bbox:[number,number,number,number];pageSize:[number,number];kind?:'figure'|'table'|'formula'};

export function checkedFigures(value:unknown,pages:number[]):TextbookFigure[]{
 if(value==null)return [];
 if(!Array.isArray(value)||value.length>2)throw new Error('Invalid source figures');
 const ids=new Set<string>();
 return value.map(item=>{
  if(!item||typeof item!=='object')throw new Error('Invalid figure');
  const f=item as Record<string,unknown>;
  if(f.kind!==undefined&&!['figure','table','formula'].includes(String(f.kind)))throw new Error('Invalid visual source kind');
  if(typeof f.id!=='string'||!/^[a-f0-9]{64}$/.test(f.id)||ids.has(f.id)||typeof f.caption!=='string'||!f.caption.trim()||f.caption.length>500||!Number.isInteger(f.pdfPage)||!pages.includes(Number(f.pdfPage)))throw new Error('Invalid figure identity');
  if(!Array.isArray(f.bbox)||f.bbox.length!==4||f.bbox.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)||f.bbox[2]<=0||f.bbox[3]<=0||f.bbox[0]+f.bbox[2]>1.001||f.bbox[1]+f.bbox[3]>1.001)throw new Error('Invalid figure crop');
  if(!Array.isArray(f.pageSize)||f.pageSize.length!==2||f.pageSize.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<1||v>10000))throw new Error('Invalid figure page');
  ids.add(f.id);
  return {id:f.id,caption:f.caption,pdfPage:Number(f.pdfPage),bbox:f.bbox as TextbookFigure['bbox'],pageSize:f.pageSize as TextbookFigure['pageSize'],...(f.kind?{kind:f.kind as TextbookFigure['kind']}:{})};
 });
}
