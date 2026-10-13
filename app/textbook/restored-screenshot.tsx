'use client';
import {useEffect,useRef,useState} from 'react';
import type {ScreenshotAttachment} from './screenshot-input';
export default function RestoredScreenshot({attachment,disabled,onAttachment,onBusy,onRemove}:{attachment:{id:string;confirmed:boolean};disabled:boolean;onAttachment:(v:ScreenshotAttachment)=>void;onBusy:(busy:boolean)=>void;onRemove:()=>void}){
 const [count,setCount]=useState(0),[loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0),[confirmed,setConfirmed]=useState(attachment.confirmed);
 const callbacks=useRef({onAttachment,onBusy});callbacks.current={onAttachment,onBusy};
 useEffect(()=>{
  const c=new AbortController();let active=true;const timer=setTimeout(()=>c.abort(),12000);setLoading(true);setError('');callbacks.current.onBusy(true);
  void (async()=>{try{const r=await fetch('/api/textbook/screenshots?id='+encodeURIComponent(attachment.id),{signal:c.signal,cache:'no-store'});const d=await r.json() as {status:string;recognition:unknown;imageCount:number;error?:string};if(!r.ok||d.status!=='done'||!d.recognition||![1,2].includes(d.imageCount))throw Error(d.error??'截图关联暂时无法恢复。');
   if(!active)return;setCount(d.imageCount);setConfirmed(attachment.confirmed);callbacks.current.onAttachment(attachment);
  }catch(e){if(active){setError(c.signal.aborted?'截图恢复超时，请重试或移除关联。':e instanceof Error?e.message:'截图恢复失败。');setConfirmed(false);callbacks.current.onAttachment({id:attachment.id,confirmed:false});}}
  finally{clearTimeout(timer);if(active){setLoading(false);callbacks.current.onBusy(false);}}})();
  return()=>{active=false;c.abort();clearTimeout(timer);callbacks.current.onBusy(false);};
 },[attachment.id,attachment.confirmed,retry]);
 return <div className="mb-3 rounded-lg border border-blue-200 bg-white p-3 text-sm">
  <p role="status" className="text-blue-900">{loading?'正在恢复已识别截图…':'已识别截图关联'}</p>
  {count>0&&!error&&<div className="my-3 flex flex-wrap gap-3">{Array.from({length:count},(_,i)=><a key={i} href={'/api/textbook/screenshots?id='+attachment.id+'&image='+i} target="_blank" rel="noreferrer"><img src={'/api/textbook/screenshots?id='+attachment.id+'&image='+i} alt={'草稿原题截图 '+(i+1)} className="h-28 max-w-52 rounded border object-contain"/></a>)}</div>}
  <p className="mt-2 text-xs text-slate-500">恢复原图关联，不覆盖你已编辑的题目文字。</p>{error&&<p role="alert" className="mt-2 text-xs text-red-800">{error}</p>}
  <div className="mt-3 flex flex-wrap gap-3">{count>0&&!error&&<button type="button" disabled={disabled||loading} onClick={()=>{setConfirmed(true);callbacks.current.onAttachment({id:attachment.id,confirmed:true});}} className="rounded border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-900">{confirmed?'已核对，可发送解析':'我已核对，保留原图解析'}</button>}{error&&<button type="button" disabled={disabled||loading} onClick={()=>setRetry(v=>v+1)} className="text-xs font-medium text-blue-800 underline">重试恢复</button>}<button type="button" disabled={disabled||loading} onClick={onRemove} className="text-xs text-slate-600 underline">移除截图关联</button></div>
 </div>;
}
