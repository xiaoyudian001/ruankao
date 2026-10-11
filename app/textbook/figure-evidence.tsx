'use client';
import {useEffect,useRef,useState} from 'react';
import {BookOpen,LoaderCircle,RefreshCw} from 'lucide-react';
import type {SourceSummary} from '../../lib/textbook/sources';
import type {TextbookFigure} from '../../lib/textbook/figures';
type SourceResult={status?:string;error?:string};

function Figure({jobId,reference,figure,onOpen}:{jobId:string;reference:SourceSummary;figure:TextbookFigure;onOpen:()=>void}){
 const container=useRef<HTMLElement>(null);const [visible,setVisible]=useState(false);
 const [image,setImage]=useState('');const [error,setError]=useState('');const [retry,setRetry]=useState(0);
 useEffect(()=>{const target=container.current;if(!target)return;const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setVisible(true);observer.disconnect();}},{rootMargin:'250px'});observer.observe(target);return()=>observer.disconnect();},[]);
 useEffect(()=>{
  if(!visible)return;
  const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;let objectUrl='';
  setImage('');setError('');const started=Date.now();
  const request={jobId,rank:reference.rank,page:figure.pdfPage};const query=new URLSearchParams(Object.entries(request).map(([k,v])=>[k,String(v)]));
  async function read(){
   try{
    const response=await fetch('/api/textbook/source?'+query,{signal:controller.signal,cache:'no-store'});
    if(response.ok&&response.headers.get('content-type')?.startsWith('image/jpeg')){
     objectUrl=URL.createObjectURL(await response.blob());if(controller.signal.aborted){URL.revokeObjectURL(objectUrl);return;}setImage(objectUrl);return;
    }
    const result=await response.json() as SourceResult;if(!response.ok||result.status==='failed')throw new Error(result.error??'原图暂时无法读取。');
    if(Date.now()-started>60000)throw new Error('原图准备较慢，请稍后重试。');timer=setTimeout(()=>void read(),1500);
   }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'原图读取失败。');}
  }
  void fetch('/api/textbook/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal}).then(async r=>{const result=await r.json() as SourceResult;if(!r.ok||result.status==='offline'||result.status==='failed')throw new Error(result.error??'原图暂时无法读取。');if(!controller.signal.aborted)void read();}).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:'原图读取失败。');});
  return()=>{controller.abort();if(timer)clearTimeout(timer);if(objectUrl)URL.revokeObjectURL(objectUrl);};
 },[visible,jobId,reference.rank,figure.pdfPage,retry]);
 const [left,top,width,height]=figure.bbox;const ratio=width*figure.pageSize[0]/(height*figure.pageSize[1]);
 return <figure ref={container} className="overflow-hidden rounded-xl border border-blue-100 bg-white">
  <figcaption className="border-b border-blue-100 bg-blue-50/40 px-4 py-3"><p className="text-sm font-semibold text-[#173f8a]">{figure.caption}</p><p className="mt-1 text-xs text-slate-500">{reference.label} · 本次回答采用的原图</p></figcaption>
  <div className="p-4">
   {image?<button type="button" onClick={onOpen} title="查看完整原 PDF 页" className="relative mx-auto block w-full max-w-xl overflow-hidden bg-white" style={{aspectRatio:ratio}}><img src={image} alt={figure.caption} onError={()=>{setImage('');setError('原图显示失败，请重试。');}} style={{position:'absolute',maxWidth:'none',width:`${100/width}%`,height:`${100/height}%`,left:`${-left/width*100}%`,top:`${-top/height*100}%`}}/></button>:error?<div role="status" className="rounded-lg bg-amber-50 p-4 text-sm leading-6 text-amber-900"><p>{error}</p><button type="button" onClick={()=>setRetry(r=>r+1)} className="mt-2 flex items-center gap-2 font-medium"><RefreshCw size={14}/>重试原图</button></div>:<p role="status" className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500"><LoaderCircle size={16} className="animate-spin"/>加载教材原图…</p>}
   <button type="button" onClick={onOpen} className="mt-3 flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-[#173f8a] hover:bg-blue-50"><BookOpen size={16}/>查看原页与正文依据</button>
  </div>
 </figure>;
}

export default function FigureEvidence({jobId,references,onOpen}:{jobId:string;references:SourceSummary[];onOpen:(reference:SourceSummary)=>void}){
 const entries=references.flatMap(reference=>(reference.figures??[]).map(figure=>({reference,figure}))).slice(0,2);
 if(!entries.length)return null;
 return <div className="mt-5 space-y-4" aria-label="本次采用的教材图示">{entries.map(({reference,figure})=><Figure key={figure.id} jobId={jobId} reference={reference} figure={figure} onOpen={()=>onOpen(reference)}/>)}</div>;
}
