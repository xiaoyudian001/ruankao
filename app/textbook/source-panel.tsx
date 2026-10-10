'use client';

import {useEffect,useRef,useState} from 'react';
import {X,ChevronLeft,ChevronRight,RefreshCw,LoaderCircle,ZoomIn,ZoomOut} from 'lucide-react';
import type {SourceReference,SourceSummary} from '../../lib/textbook/sources';

export type SourceSelection={jobId:string;reference:SourceSummary};
type SourceResponse={reference?:SourceReference;status?:string;error?:string};

export default function SourcePanel({selection,onClose}:{selection:SourceSelection;onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [page,setPage]=useState(selection.reference.pdfPages[0]);
  const [reference,setReference]=useState<SourceReference|null>(null);
  const [image,setImage]=useState('');const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);const [tab,setTab]=useState<'page'|'passage'>('page');
  const [retry,setRetry]=useState(0);const [zoom,setZoom]=useState(100);
  useEffect(()=>{
    const focus=document.activeElement as HTMLElement|null;const x=window.scrollX,y=window.scrollY;
    const overflow=document.body.style.overflow;document.body.style.overflow='hidden';
    dialog.current?.showModal();
    return()=>{dialog.current?.close();document.body.style.overflow=overflow;focus?.focus({preventScroll:true});window.scrollTo(x,y);};
  },[]);
  useEffect(()=>{
    const controller=new AbortController();let objectUrl='';let timer:ReturnType<typeof setTimeout>|undefined;
    setLoading(true);setError('');setImage('');setZoom(100);
    const request={jobId:selection.jobId,rank:selection.reference.rank,page};
    const query=new URLSearchParams(Object.entries(request).map(([k,v])=>[k,String(v)]));
    const started=Date.now();
    async function load(){
      try{
        const response=await fetch('/api/textbook/source?'+query,{signal:controller.signal,cache:'no-store'});
        if(response.ok&&response.headers.get('content-type')?.startsWith('image/jpeg')){
          objectUrl=URL.createObjectURL(await response.blob());if(controller.signal.aborted){URL.revokeObjectURL(objectUrl);return;}
          setImage(objectUrl);setLoading(false);return;
        }
        const result=await response.json() as SourceResponse;
        if(!response.ok||result.status==='failed')throw new Error(result.error??'原页暂时无法读取。');
        if(Date.now()-started>60000)throw new Error('原页准备时间较长，请稍后点击重试。');
        timer=setTimeout(()=>void load(),2000);
      }catch(e){if(!controller.signal.aborted){setError(e instanceof Error?e.message:'原页读取失败。');setLoading(false);}}
    }
    void(async()=>{
      try{
        const response=await fetch('/api/textbook/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal});
        const result=await response.json() as SourceResponse;if(!response.ok)throw new Error(result.error??'引用读取失败。');
        if(controller.signal.aborted)return;
        setReference(result.reference??null);
        if(result.status==='offline'||result.status==='failed')throw new Error(result.error??'原页暂不可用。');
        await load();
      }catch(e){if(!controller.signal.aborted){setError(e instanceof Error?e.message:'引用读取失败。');setLoading(false);}}
    })();
    return()=>{controller.abort();if(timer)clearTimeout(timer);if(objectUrl)URL.revokeObjectURL(objectUrl);};
  },[selection.jobId,selection.reference.rank,page,retry]);
  const pages=selection.reference.pdfPages;const index=pages.indexOf(page);
  return <dialog ref={dialog} onCancel={onClose} onClose={onClose} aria-labelledby="source-title" className="fixed inset-y-0 left-auto right-0 m-0 h-dvh max-h-none w-full max-w-[780px] border-0 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/25 sm:rounded-l-2xl">
    <div className="flex h-full flex-col">
      <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-5"><div><p className="text-xs font-semibold tracking-wider text-[#173f8a]">教材出处 · 片段 {selection.reference.rank}</p><h2 id="source-title" className="mt-2 text-base font-bold leading-7">{selection.reference.label}</h2></div><button type="button" autoFocus onClick={onClose} aria-label="关闭引用查看" className="shrink-0 rounded-lg p-2 text-slate-600 hover:bg-slate-100"><X size={20}/></button></header>
      <div role="tablist" aria-label="引用内容" className="flex gap-2 border-b border-slate-200 px-5 pt-3"><button role="tab" id="source-page-tab" aria-controls="source-content" aria-selected={tab==='page'} onClick={()=>setTab('page')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab==='page'?'border-[#173f8a] text-[#173f8a]':'border-transparent text-slate-500'}`}>原 PDF 页</button><button role="tab" id="source-passage-tab" aria-controls="source-content" aria-selected={tab==='passage'} onClick={()=>setTab('passage')} className={`border-b-2 px-4 py-3 text-sm font-semibold ${tab==='passage'?'border-[#173f8a] text-[#173f8a]':'border-transparent text-slate-500'}`}>本次检索片段</button></div>
      {tab==='page'&&<div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-5 py-3"><div className="flex items-center gap-2"><button aria-label="引用的上一页" disabled={index<=0} onClick={()=>setPage(pages[index-1])} className="rounded p-1.5 hover:bg-white disabled:opacity-30"><ChevronLeft size={18}/></button><span className="text-sm font-medium">PDF 第 {page} 页</span><button aria-label="引用的下一页" disabled={index===pages.length-1} onClick={()=>setPage(pages[index+1])} className="rounded p-1.5 hover:bg-white disabled:opacity-30"><ChevronRight size={18}/></button></div><div className="flex items-center gap-2"><button aria-label="缩小原页" disabled={zoom<=100} onClick={()=>setZoom(z=>z-25)} className="rounded p-1.5 hover:bg-white disabled:opacity-30"><ZoomOut size={17}/></button><span className="text-xs text-slate-500">{zoom}%</span><button aria-label="放大原页" disabled={zoom>=200} onClick={()=>setZoom(z=>z+25)} className="rounded p-1.5 hover:bg-white disabled:opacity-30"><ZoomIn size={17}/></button></div></div>}
      <div id="source-content" role="tabpanel" aria-labelledby={tab==='page'?'source-page-tab':'source-passage-tab'} tabIndex={0} className="min-h-0 flex-1 overflow-auto bg-slate-50 p-4 sm:p-5">
        {tab==='passage'?<div className="rounded-xl border border-slate-200 bg-white p-5"><p className="mb-4 text-xs leading-6 text-slate-500">这是生成该回答时实际提供给模型的片段，编号与答案引用一致。它可能跨越多页。</p>{reference?<p className="whitespace-pre-wrap break-words text-base leading-8">{reference.content}</p>:<p role="status" className="text-sm text-slate-500">{error||'正在读取检索片段…'}</p>}</div>:<>{pages.length>1&&<p className="mb-3 text-xs text-slate-500">片段跨页，可切换上方页码查看引用范围。</p>}{loading?<p role="status" className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500"><LoaderCircle size={18} className="animate-spin"/>正在从原 PDF 准备第 {page} 页…</p>:error?<div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm leading-7 text-amber-900"><p>{error}</p><button onClick={()=>setRetry(r=>r+1)} className="mt-3 flex items-center gap-2 font-semibold"><RefreshCw size={16}/>重试加载原页</button></div>:image&&<img src={image} alt={`原教材 PDF 第${page}页`} onError={()=>setError('图片显示失败，请重试。')} style={{width:`${zoom}%`,maxWidth:'none'}} className="h-auto rounded-lg border border-slate-200 bg-white shadow-sm"/>}</>}
      </div><footer className="border-t border-slate-200 px-5 py-3 text-xs leading-6 text-slate-500">教材页码用于查书，PDF 页码用于定位电子文件。关闭后返回当前答案。</footer>
    </div>
  </dialog>;
}
