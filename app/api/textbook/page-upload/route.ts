import {BOOK_SHA,PAGE_FINISH_SQL} from '../../../../lib/textbook/sources';
import {bridgeAuth,database,json,now,runtime} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';

export async function PUT(request:Request){
  if(!bridgeAuth(request))return json({error:'Unauthorized'},401);
  const page=Number(request.headers.get('x-pdf-page'));const lease=request.headers.get('x-page-lease');
  if(!Number.isInteger(page)||page<1||page>728||!validId(lease)||request.headers.get('content-type')!=='image/jpeg')return json({error:'Invalid page upload'},400);
  try{
    const current=await database().prepare("SELECT page FROM textbook_pages WHERE page=? AND status='running' AND lease=? AND updated_at>=?").bind(page,lease,now()-90).first();
    if(!current)return json({error:'Expired page lease'},409);
    const maximum=2*1024*1024;
    if(Number(request.headers.get('content-length')??0)>maximum)return json({error:'Page too large'},413);
    const reader=request.body?.getReader();if(!reader)return json({error:'Empty page'},400);
    const parts:Uint8Array[]=[];let size=0;
    for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>maximum){await reader.cancel();return json({error:'Page too large'},413);}parts.push(value);}
    const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
    if(size<100||bytes[0]!==255||bytes[1]!==216||bytes[size-2]!==255||bytes[size-1]!==217)return json({error:'Invalid JPEG'},400);
    const bucket=runtime().BUCKET;if(!bucket)return json({error:'Storage unavailable'},503);
    // Lease-specific keys prevent an expired uploader overwriting a newer page.
    const key=`textbook/${BOOK_SHA}/${page}/${lease}.jpg`;
    await bucket.put(key,bytes,{httpMetadata:{contentType:'image/jpeg'}});
    const done=await database().prepare(PAGE_FINISH_SQL).bind(key,now(),page,lease,now()-90).first();
    if(!done){await bucket.delete(key);return json({error:'Expired page lease'},409);}
    return json({ok:true});
  }catch{return json({error:'Page upload unavailable'},503);}
}
