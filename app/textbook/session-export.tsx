'use client';
import {useEffect,useRef,useState} from 'react';
import {Download,LoaderCircle} from 'lucide-react';
export default function SessionExport({sessionId}:{sessionId:string|null}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');const active=useRef<AbortController|null>(null),objectUrl=useRef<string|null>(null),release=useRef<ReturnType<typeof setTimeout>|null>(null);
 useEffect(()=>{setError('');setBusy(false);return()=>{active.current?.abort();active.current=null;if(release.current)clearTimeout(release.current);if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current=null;};},[sessionId]);
 async function download(){
  if(!sessionId||busy)return;setBusy(true);setError('');const c=new AbortController();active.current=c;const timer=setTimeout(()=>c.abort(),15000);
  try{const r=await fetch('/api/textbook/export?sessionId='+encodeURIComponent(sessionId),{signal:c.signal,cache:'no-store'});if(!r.ok){const d=await r.json() as {error?:string};throw Error(d.error??'导出失败，请重试。');}const blob=await r.blob();if(active.current!==c)return;
   if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);if(release.current)clearTimeout(release.current);const url=URL.createObjectURL(blob);objectUrl.current=url;const link=document.createElement('a');link.href=url;link.download='软考问答-'+sessionId.slice(0,8)+'.md';document.body.appendChild(link);link.click();link.remove();release.current=setTimeout(()=>{URL.revokeObjectURL(url);if(objectUrl.current===url)objectUrl.current=null;},30000);
  }catch(e){if(active.current===c)setError(c.signal.aborted?'导出超时，请重试。':e instanceof Error?e.message:'导出失败，请重试。');}
  finally{clearTimeout(timer);if(active.current===c){active.current=null;setBusy(false);}}
 }
 return <div className="text-right"><button type="button" disabled={!sessionId||busy} onClick={()=>void download()} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-30">{busy?<LoaderCircle size={14} className="animate-spin"/>:<Download size={14}/>}导出 Markdown</button>{error&&<p role="alert" className="mt-2 max-w-64 text-xs text-red-800">{error}</p>}</div>;
}
