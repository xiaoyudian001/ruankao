'use client';
import {useState} from 'react';
import {Bookmark,Check,LoaderCircle} from 'lucide-react';

export default function FavoriteAction({jobId,saved,onSaved}:{jobId:string;saved:boolean;onSaved:()=>void}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(){
    if(busy||saved)return;setBusy(true);setError('');
    try{const r=await fetch('/api/textbook/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'favorite',jobId})});const d=await r.json() as {error?:string};if(!r.ok)throw new Error(d.error??'收藏失败。');onSaved();}catch(e){setError(e instanceof Error?e.message:'收藏失败，请重试。');}finally{setBusy(false);}
  }
  return <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-3"><button disabled={busy||saved} onClick={()=>void save()} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${saved?'bg-blue-50 text-[#173f8a]':'text-slate-600 hover:bg-slate-100'} disabled:opacity-70`}>{busy?<LoaderCircle size={15} className="animate-spin"/>:saved?<Check size={15}/>:<Bookmark size={15}/>} {saved?'已收藏':'收藏答案'}</button>{saved&&<a href="/review?tab=favorites" className="text-sm font-medium text-blue-800 hover:underline">制作复习卡片 →</a>}{error&&<p role="alert" className="text-xs text-red-700">{error}</p>}</div>;
}
