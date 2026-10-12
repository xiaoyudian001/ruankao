export const MAX_IMAGE_BYTES=2*1024*1024;
export const MAX_UPLOAD_BYTES=2*MAX_IMAGE_BYTES+100000;
export type Recognition={question:string;notes:string};
export type ScreenshotManifest={recognitionId:string;images:{key:string;sha:string;width:number;height:number;size:number}[]};
const uuid=(s:unknown):s is string=>typeof s==='string'&&/^[a-f0-9-]{36}$/i.test(s);
export function pngInfo(bytes:Uint8Array){
 if(bytes.length<33||bytes.length>MAX_IMAGE_BYTES||[137,80,78,71,13,10,26,10].some((v,i)=>bytes[i]!==v)||String.fromCharCode(...bytes.slice(12,16))!=='IHDR')throw new Error('请上传有效的 PNG 截图，每张不超过 2 MB。');
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),width=view.getUint32(16),height=view.getUint32(20);
 if(view.getUint32(8)!==13||width<32||height<32||width>4000||height>4000||width*height>8000000)throw new Error('截图尺寸无效，请裁剪到一道题后上传。');
 return {width,height};
}
export function validateRecognition(v:unknown):Recognition{
 if(!v||typeof v!=='object'||Array.isArray(v))throw new Error('Invalid recognition');
 const x=v as Record<string,unknown>;
 if(Object.keys(x).sort().join(',')!=='notes,question'||typeof x.question!=='string'||!x.question.trim()||x.question.trim().length>2000||typeof x.notes!=='string'||x.notes.length>1000||/<\/?(?:think|script|iframe)\b/i.test(x.question+x.notes))throw new Error('Invalid recognition');
 return {question:x.question.trim(),notes:x.notes.trim()};
}
export function parseManifest(raw:unknown):ScreenshotManifest{
 const v=typeof raw==='string'?JSON.parse(raw):raw;
 if(!v||!uuid(v.recognitionId)||!Array.isArray(v.images)||!v.images.length||v.images.length>2)throw new Error('Invalid screenshot manifest');
 for(const [i,x] of v.images.entries())if(!x||!/^[a-f0-9]{64}$/.test(x.sha)||x.key!==`exam-screenshots/${v.recognitionId}/${i}-${x.sha}.png`||!Number.isInteger(x.width)||!Number.isInteger(x.height)||x.width<32||x.height<32||x.width>4000||x.height>4000||x.width*x.height>8000000||!Number.isInteger(x.size)||x.size<=0||x.size>MAX_IMAGE_BYTES)throw new Error('Invalid screenshot image');
 return {recognitionId:v.recognitionId,images:v.images.map((x:ScreenshotManifest['images'][number])=>({key:x.key,sha:x.sha,width:x.width,height:x.height,size:x.size}))};
}
export async function boundedUpload(request:Request){
 if(Number(request.headers.get('content-length')??0)>MAX_UPLOAD_BYTES)throw new Error('截图总大小超出限制。');
 const reader=request.body?.getReader();if(!reader)throw new Error('缺少截图。');
 const chunks:Uint8Array[]=[];let size=0;
 for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>MAX_UPLOAD_BYTES){await reader.cancel();throw new Error('截图总大小超出限制。');}chunks.push(value);}
 const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
 return new Response(bytes,{headers:{'Content-Type':request.headers.get('content-type')??''}}).formData();
}
