'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {MessageSquare,Plus,Search,Pencil,Trash2,LoaderCircle,RefreshCw} from 'lucide-react';
type Session={id:string;title:string;updated_at:number;pending:boolean};
export default function SessionSidebar({selected,disabled,refreshKey,onSelect,onDeleted}:{selected:string|null;disabled:boolean;refreshKey:string;onSelect:(id:string|null)=>void;onDeleted:(id:string)=>void}){
 const [search,setSearch]=useState(''),[query,setQuery]=useState(''),[sessions,setSessions]=useState<Session[]>([]),[cursor,setCursor]=useState<string|null>(null);
 const [loading,setLoading]=useState(false),[mutating,setMutating]=useState(false),[error,setError]=useState('');
 const [editing,setEditing]=useState<string|null>(null),[title,setTitle]=useState(''),[deleting,setDeleting]=useState<Session|null>(null);
 const read=useRef<AbortController|null>(null),mounted=useRef(true);
 useEffect(()=>{const timer=setTimeout(()=>setQuery(search.trim()),250);return()=>clearTimeout(timer);},[search]);
 const load=useCallback(async(after:string|null=null)=>{
  read.current?.abort();const controller=new AbortController();read.current=controller;setLoading(true);setError('');
  const timer=setTimeout(()=>controller.abort(),12000);
  try{const p=new URLSearchParams({q:query});if(after)p.set('cursor',after);const r=await fetch('/api/textbook/sessions?'+p,{signal:controller.signal,cache:'no-store'});const d=await r.json() as {sessions:Session[];nextCursor:string|null;error?:string};if(!r.ok)throw Error(d.error??'历史会话读取失败。');
   if(read.current!==controller||!mounted.current)return;setSessions(previous=>after?[...previous,...d.sessions.filter(s=>!previous.some(p=>p.id===s.id))]:d.sessions);setCursor(d.nextCursor);
  }catch(e){if(read.current===controller&&mounted.current)setError(controller.signal.aborted?'历史会话读取超时，请重试。':e instanceof Error?e.message:'历史会话读取失败。');}
  finally{clearTimeout(timer);if(read.current===controller&&mounted.current)setLoading(false);}
 },[query]);
 const currentLoad=useRef(load);currentLoad.current=load;
 useEffect(()=>{mounted.current=true;void load();return()=>{mounted.current=false;read.current?.abort();};},[load,refreshKey]);
 async function change(method:'PATCH'|'DELETE',id:string){
  if(disabled||mutating)return;setMutating(true);setError('');const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{const r=await fetch('/api/textbook/sessions',{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:id,...(method==='PATCH'?{title}: {})}),signal:controller.signal});const d=await r.json() as {error?:string};if(!r.ok)throw Error(d.error??'修改失败，请重试。');if(!mounted.current)return;
   if(method==='DELETE'){setDeleting(null);setSessions(previous=>previous.filter(s=>s.id!==id));onDeleted(id);}else setEditing(null);await currentLoad.current();
  }catch(e){if(mounted.current)setError(controller.signal.aborted?'修改结果未确认，请重试。':e instanceof Error?e.message:'修改失败，请重试。');}
  finally{clearTimeout(timer);if(mounted.current)setMutating(false);}
 }
 return <div className="flex h-full flex-col">
  <button type="button" disabled={disabled||mutating} onClick={()=>onSelect(null)} className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#173f8a] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"><Plus size={18}/>新建会话</button>
  <div className="mb-3 mt-5 flex items-center justify-between"><h2 className="text-sm font-semibold text-slate-500">历史会话</h2><button type="button" disabled={loading||mutating} aria-label="刷新历史会话" onClick={()=>void load()} className="rounded p-1.5 text-slate-500 hover:bg-slate-100"><RefreshCw size={15}/></button></div>
  <label className="mb-3 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-slate-400"><Search size={16}/><span className="sr-only">搜索会话标题、问题或答案</span><input value={search} maxLength={100} onChange={e=>setSearch(e.target.value)} placeholder="搜索标题或问答内容" className="min-w-0 flex-1 bg-transparent text-sm text-slate-700 outline-none"/></label>
  {error&&<p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-xs leading-5 text-red-800">{error}</p>}
  <div className="max-h-64 space-y-2 overflow-auto lg:max-h-none lg:flex-1">
   {loading&&!sessions.length?<p role="status" className="py-3 text-sm text-slate-500">读取历史会话…</p>:!sessions.length?<p className="py-3 text-sm text-slate-400">{query?'没有匹配的会话。':'提问后会自动保存会话。'}</p>:sessions.map(s=><div key={s.id} className={`rounded-lg border ${selected===s.id?'border-blue-200 bg-blue-50':'border-transparent hover:bg-slate-50'}`}>
    {editing===s.id?<form onSubmit={e=>{e.preventDefault();void change('PATCH',s.id);}} className="p-2"><label className="sr-only" htmlFor={'session-name-'+s.id}>会话名称</label><input id={'session-name-'+s.id} autoFocus maxLength={80} value={title} disabled={mutating} onChange={e=>setTitle(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')setEditing(null);}} className="w-full rounded border border-blue-300 bg-white p-2 text-sm outline-none"/><div className="mt-2 flex gap-3 text-xs"><button disabled={disabled||mutating||!title.trim()} className="font-semibold text-blue-800">保存</button><button type="button" disabled={mutating} onClick={()=>setEditing(null)} className="text-slate-500">取消</button></div></form>:<><button type="button" disabled={disabled||mutating} onClick={()=>onSelect(s.id)} title={s.title} className="flex w-full items-start gap-2 p-3 text-left text-sm text-slate-700"><MessageSquare className="mt-0.5 shrink-0" size={16}/><span className="line-clamp-2 break-words">{s.title}</span></button><div className="flex items-center justify-between px-3 pb-2"><span className="text-[11px] text-slate-400">{s.pending?'任务处理中':new Date(s.updated_at*1000).toLocaleDateString('zh-CN')}</span><div className="flex gap-1"><button type="button" disabled={disabled||mutating} aria-label={'重命名会话：'+s.title} onClick={()=>{setEditing(s.id);setTitle(s.title);setDeleting(null);}} className="rounded p-1.5 text-slate-400 hover:bg-white hover:text-blue-800 disabled:opacity-30"><Pencil size={14}/></button><button type="button" disabled={disabled||mutating||s.pending} title={s.pending?'任务完成后才能删除':'删除会话'} aria-label={'删除会话：'+s.title} onClick={()=>{setDeleting(s);setEditing(null);}} className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-700 disabled:opacity-30"><Trash2 size={14}/></button></div></div></>}
   </div>)}
   {cursor&&<button type="button" disabled={loading} onClick={()=>void load(cursor)} className="w-full rounded-lg border border-slate-200 py-2 text-sm text-slate-600">{loading?'读取中…':'加载更多会话'}</button>}
  </div>
  {deleting&&<div role="group" aria-label="确认删除会话" className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm leading-6 text-red-900"><p className="font-semibold">删除“{deleting.title}”？</p><p className="mt-1 text-xs leading-5">从聊天历史中移除。已收藏答案、复习卡片及其引用会保留。</p><div className="mt-3 flex gap-3"><button type="button" disabled={disabled||mutating} onClick={()=>void change('DELETE',deleting.id)} className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40">{mutating?<LoaderCircle size={14} className="animate-spin"/>:'确认删除'}</button><button type="button" disabled={mutating} onClick={()=>setDeleting(null)} className="text-xs text-slate-600">取消</button></div></div>}
 </div>;
}
