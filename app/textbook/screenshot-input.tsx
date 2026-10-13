'use client';
import {useEffect,useRef,useState} from 'react';
import {ImagePlus,LoaderCircle,Trash2,Check} from 'lucide-react';
import {MAX_IMAGE_BYTES,type Recognition} from '../../lib/textbook/screenshots';
import RestoredScreenshot from './restored-screenshot';
export type ScreenshotAttachment={id:string|null;confirmed:boolean}|null;
type Photo={file:File;url:string};
export async function normalizeScreenshot(file:File):Promise<File>{
 if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>10*1024*1024)throw new Error('请选择 PNG、JPEG 或 WebP 图片，原图不超过 10 MB。');
 const bitmap=await createImageBitmap(file);
 try{
  if(bitmap.width<32||bitmap.height<32||bitmap.width*bitmap.height>40000000)throw new Error('请先裁剪截图，只保留一道题。');
  const scale=Math.min(1,2200/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('图片处理不可用，请换一个浏览器。');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
  const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('图片转换失败。')),'image/png'));
  if(blob.size>MAX_IMAGE_BYTES)throw new Error('截图转换后超过 2 MB，请裁剪到题目区域再上传。');
  return new File([blob],'question.png',{type:'image/png'});
 }finally{bitmap.close();}
}
export default function ScreenshotInput({enabled,disabled,initialAttachment,onAttachment,onRecognized,onBusy}:{enabled:boolean;disabled:boolean;initialAttachment?:ScreenshotAttachment;onAttachment:(v:ScreenshotAttachment)=>void;onRecognized:(text:string)=>void;onBusy:(v:boolean)=>void}){
 const [photos,setPhotos]=useState<Photo[]>([]),[processing,setProcessing]=useState(false),[recognizing,setRecognizing]=useState(false),[jobId,setJobId]=useState<string|null>(null),[stage,setStage]=useState(''),[notes,setNotes]=useState(''),[recognized,setRecognized]=useState(false),[confirmed,setConfirmed]=useState(false),[error,setError]=useState('');
 const input=useRef<HTMLInputElement>(null),photosRef=useRef<Photo[]>([]),uploadId=useRef<string|null>(null),busyRef=useRef(false),mounted=useRef(true),failedJob=useRef(false);
 const callbacks=useRef({onAttachment,onRecognized,onBusy});callbacks.current={onAttachment,onRecognized,onBusy};
 const [restored,setRestored]=useState(initialAttachment?.id?{id:initialAttachment.id,confirmed:initialAttachment.confirmed}:null);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;photosRef.current.forEach(p=>URL.revokeObjectURL(p.url));callbacks.current.onBusy(false);};},[]);
 async function add(files:File[]){
  if(disabled||busyRef.current||restored)return;
  if(photosRef.current.length+files.length>2){setError('同一道题最多两张截图，请先移除多余图片。');return;}
  busyRef.current=true;setProcessing(true);callbacks.current.onBusy(true);setError('');const prepared:Photo[]=[];
  try{for(const f of files){const file=await normalizeScreenshot(f);prepared.push({file,url:URL.createObjectURL(file)});}if(!mounted.current){prepared.forEach(p=>URL.revokeObjectURL(p.url));return;}photosRef.current=[...photosRef.current,...prepared];setPhotos(photosRef.current);setJobId(null);uploadId.current=null;setRecognized(false);setConfirmed(false);setNotes('');setStage('');callbacks.current.onAttachment({id:null,confirmed:false});}
  catch(e){prepared.forEach(p=>URL.revokeObjectURL(p.url));if(mounted.current)setError(e instanceof Error?e.message:'图片处理失败。');}
  finally{busyRef.current=false;if(mounted.current){setProcessing(false);callbacks.current.onBusy(false);}}
 }
 useEffect(()=>{function paste(e:ClipboardEvent){if(disabled||restored||!document.activeElement?.closest('form'))return;const files=Array.from(e.clipboardData?.files??[]).filter(f=>f.type.startsWith('image/'));if(files.length){e.preventDefault();void add(files);}}document.addEventListener('paste',paste);return()=>document.removeEventListener('paste',paste);},[disabled,restored]);
 function remove(index:number){const removed=photosRef.current[index];URL.revokeObjectURL(removed.url);photosRef.current=photosRef.current.filter((_,i)=>i!==index);setPhotos(photosRef.current);setJobId(null);uploadId.current=null;setRecognized(false);setConfirmed(false);setNotes('');setStage('');setError('');callbacks.current.onAttachment(photosRef.current.length?{id:null,confirmed:false}:null);}
 async function recognize(){
  if(!enabled||disabled||busyRef.current||!photos.length)return;if(recognized){uploadId.current=null;setRecognized(false);setConfirmed(false);callbacks.current.onAttachment({id:null,confirmed:false});}busyRef.current=true;setRecognizing(true);callbacks.current.onBusy(true);setError('');setStage('上传截图…');failedJob.current=false;
  if(!uploadId.current)uploadId.current=crypto.randomUUID();
  try{const form=new FormData();form.set('requestId',uploadId.current);photos.forEach(p=>form.append('images',p.file));const response=await fetch('/api/textbook/screenshots',{method:'POST',body:form});const value=await response.json() as {id:string;error?:string};if(!response.ok)throw new Error(value.error??'上传失败，请重试。');if(mounted.current)setJobId(value.id);
   const deadline=Date.now()+300000;
   while(mounted.current&&Date.now()<deadline){const r=await fetch('/api/textbook/screenshots?id='+encodeURIComponent(value.id),{cache:'no-store'});const data=await r.json() as {status:string;recognition:Recognition|null;error?:string};if(!r.ok)throw new Error(data.error??'识别状态暂不可用，请重试。');if(data.status==='done'&&data.recognition){setNotes(data.recognition.notes);setRecognized(true);setConfirmed(false);setStage('请在下方输入框核对、修改题干和全部选项。');callbacks.current.onRecognized(data.recognition.question);callbacks.current.onAttachment({id:value.id,confirmed:false});return;}if(data.status==='failed'){failedJob.current=true;throw new Error(data.error??'识别失败，请换清晰截图。');}setStage(data.status==='queued'?'等待电脑领取截图…':'正在识别题干、选项和图表条件…');await new Promise(resolve=>setTimeout(resolve,2000));}
   throw new Error('识别仍未完成，可点击重试读取同一任务。');
  }catch(e){if(mounted.current){setError(e instanceof Error?e.message:'截图识别失败。');setStage('');if(failedJob.current){uploadId.current=null;setJobId(null);}}}
  finally{busyRef.current=false;if(mounted.current){setRecognizing(false);callbacks.current.onBusy(false);}}
 }
 return <div className="mb-3 rounded-xl border border-blue-100 bg-blue-50/50 p-3">
  {restored&&<RestoredScreenshot attachment={restored} disabled={disabled} onAttachment={onAttachment} onBusy={onBusy} onRemove={()=>{setRestored(null);callbacks.current.onAttachment(null);}}/>}
  <div className="flex flex-wrap items-center gap-3"><input ref={input} type="file" multiple accept="image/png,image/jpeg,image/webp" className="sr-only" aria-label="选择题目截图" disabled={disabled||processing||recognizing||Boolean(restored)} onChange={e=>{void add(Array.from(e.target.files??[]));e.target.value='';}}/><button type="button" disabled={disabled||processing||recognizing||Boolean(restored)} onClick={()=>input.current?.click()} className="flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-900 disabled:opacity-40"><ImagePlus size={16}/>上传题目截图</button><span className="text-xs text-slate-500">支持粘贴图片 · 同一道题最多两张 · 图表会保留</span></div>
  {photos.length>0&&<><div className="my-3 flex flex-wrap gap-3">{photos.map((photo,i)=><div key={photo.url} className="relative"><a href={photo.url} target="_blank" rel="noreferrer" title="查看截图"><img src={photo.url} alt={`题目截图 ${i+1}`} className="h-28 max-w-52 rounded-lg border border-slate-200 bg-white object-contain"/></a><button type="button" onClick={()=>remove(i)} disabled={disabled||processing||recognizing||Boolean(restored)} aria-label={`移除截图 ${i+1}`} className="absolute right-1 top-1 rounded bg-white p-1.5 text-slate-600 shadow disabled:opacity-40"><Trash2 size={14}/></button></div>)}</div><div className="flex flex-wrap items-center gap-3"><button type="button" disabled={!enabled||disabled||processing||recognizing} onClick={()=>void recognize()} className="rounded-lg bg-[#173f8a] px-3 py-2 text-sm font-medium text-white disabled:opacity-40">{recognizing?'识别中…':recognized?'重新识别':error?'重试识别':'识别题目'}</button>{recognized&&<button type="button" disabled={disabled||recognizing} onClick={()=>{if(jobId){setConfirmed(true);callbacks.current.onAttachment({id:jobId,confirmed:true});}}} className={`flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium ${confirmed?'border-emerald-200 bg-emerald-50 text-emerald-800':'border-blue-300 bg-white text-blue-900'}`}><Check size={15}/>{confirmed?'已核对，可发送解析':'我已核对文字，保留原图解析'}</button>}</div></>}
  {(processing||stage)&&<p role="status" className="mt-2 flex items-center gap-2 text-sm text-slate-600">{(processing||recognizing)&&<LoaderCircle size={14} className="animate-spin"/>}{processing?'正在处理图片…':stage}</p>}
  {notes&&<p className="mt-2 whitespace-pre-wrap text-sm text-amber-900">识别注意：{notes}</p>}{error&&<p role="alert" className="mt-2 text-sm text-red-800">{error}</p>}
  {restored&&<p className="mt-2 text-xs text-slate-500">上传新截图前请先移除旧关联。</p>}
  {photos.length>0&&<p className="mt-2 text-xs text-slate-500">{!enabled?'截图识题尚未连接，请稍后刷新连接。':'识别会填入下方输入框，请特别核对否定词、数字、公式和选项。'}图片将随题发送至现有 MiniMax 服务。未完成识别的本地截图无法在刷新后恢复，请先完成识别。</p>}
 </div>;
}
