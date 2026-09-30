'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen, MessageSquare, Plus, Send, RefreshCw, LoaderCircle, Copy, Check, Home } from 'lucide-react';
import Answer from './answer';
import Link from 'next/link';

type Session={id:string;title:string;updated_at:number};
type Message={id:string;question:string;status:string;answer:string|null;error:string|null;elapsed_ms:number|null};
const suggestions=['解释一下什么是MTBF，并指出教材出处。','系统架构设计师有哪些职责？','事件驱动架构由哪四个部分组成？'];

export default function TextbookChat(){
  const [sessions,setSessions]=useState<Session[]>([]);const [session,setSession]=useState<string|null>(null);
  const [messages,setMessages]=useState<Message[]>([]);const [online,setOnline]=useState(false);const [checking,setChecking]=useState(true);
  const [draft,setDraft]=useState('');const [notice,setNotice]=useState('');const [sending,setSending]=useState(false);const [copied,setCopied]=useState('');
  const request=useRef<{question:string;sessionId:string|null;id:string}|null>(null);const end=useRef<HTMLDivElement>(null);const active=useRef<string|null>(null);
  const refresh=useCallback(async(signal?:AbortSignal)=>{
    const current=active.current;
    try{const r=await fetch('/api/textbook/chat'+(current?'?sessionId='+encodeURIComponent(current):''),{signal,cache:'no-store'});const data=await r.json() as {error?:string;sessions:Session[];messages:Message[];online:boolean;job:{session_id:string}};if(!r.ok)throw new Error(data.error??'连接暂时不可用');if(active.current!==current)return;setSessions(data.sessions);setMessages(data.messages);setOnline(data.online);setChecking(false);}
    catch(e){if(signal?.aborted)return;setOnline(false);setChecking(false);setNotice(e instanceof Error?e.message:'连接暂时不可用。');}
  },[]);
  useEffect(()=>{const controller=new AbortController();void refresh(controller.signal);const timer=setInterval(()=>void refresh(controller.signal),3000);return()=>{controller.abort();clearInterval(timer);};},[refresh,session]);
  const pending=messages.some(m=>m.status==='queued'||m.status==='running');
  const messageState=messages.map(m=>m.status).join(',');
  useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth',block:'end'});},[messages.length,messageState]);
  function select(id:string|null){active.current=id;setSession(id);setMessages([]);setNotice('');request.current=null;}
  async function send(question=draft){
    question=question.trim();if(!question||sending||pending)return;setSending(true);setNotice('');
    if(!request.current||request.current.question!==question||request.current.sessionId!==session)request.current={question,sessionId:session,id:crypto.randomUUID()};
    const value=request.current;
    try{const r=await fetch('/api/textbook/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,sessionId:session,requestId:value.id})});const data=await r.json() as {error?:string;sessions:Session[];messages:Message[];online:boolean;job:{session_id:string}};if(!r.ok)throw new Error(data.error??'发送失败，请重试。');request.current=null;setDraft('');active.current=data.job.session_id;setSession(data.job.session_id);await refresh();}
    catch(e){setDraft(question);setNotice(e instanceof Error?e.message:'发送失败，问题已保留。');}
    finally{setSending(false);}
  }
  async function copy(id:string,text:string){try{await navigator.clipboard.writeText(text);setCopied(id);setTimeout(()=>setCopied(''),2000);}catch{setNotice('复制失败，请手动选择答案文字。');}}
  return <main className="min-h-screen bg-[#f4f7fb] text-slate-950">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8"><Link href="/" target="_top" prefetch={false} className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#173f8a] text-white"><BookOpen size={21}/></span><span><b className="block">软考冲刺台</b><span className="text-sm text-slate-500">教材问答</span></span></Link><div className="flex items-center gap-4"><span role="status" className={`rounded-full px-3 py-1.5 text-sm font-medium ${online?'bg-emerald-50 text-emerald-700':'bg-slate-100 text-slate-600'}`}>{checking?'检查连接…':online?'电脑已连接':'电脑未连接'}</span><Link href="/" target="_top" prefetch={false} className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-800"><Home size={16}/>复习总览</Link></div></div></header>
    <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-8 lg:grid-cols-[250px_1fr]">
      <aside className="rounded-2xl border border-slate-200 bg-white p-4 lg:sticky lg:top-5 lg:h-[calc(100dvh-130px)]"><button disabled={sending} onClick={()=>select(null)} className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#173f8a] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"><Plus size={18}/>新建会话</button><h2 className="mb-3 mt-6 text-sm font-semibold text-slate-500">最近会话</h2><div className="flex max-h-40 gap-2 overflow-auto lg:max-h-[calc(100dvh-310px)] lg:flex-col">{sessions.length===0?<p className="text-sm text-slate-400">提问后会自动保存。</p>:sessions.map(s=><button disabled={sending} key={s.id} onClick={()=>select(s.id)} title={s.title} className={`flex min-w-40 items-start gap-2 rounded-lg p-3 text-left text-sm lg:min-w-0 ${session===s.id?'bg-blue-50 font-medium text-[#173f8a]':'text-slate-600 hover:bg-slate-50'}`}><MessageSquare className="mt-0.5 shrink-0" size={16}/><span className="line-clamp-2 break-words">{s.title}</span></button>)}</div></aside>
      <section className="flex min-h-[calc(100dvh-130px)] min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-7"><div><h1 className="text-lg font-bold">教材检索与备考问答</h1><p className="mt-1 text-sm text-slate-500">《系统架构设计师教程》第 2 版 · 回答附教材与 PDF 页码</p></div><button onClick={()=>void refresh()} aria-label="刷新连接状态" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><RefreshCw size={18}/></button></div>
        {!checking&&!online&&<div className="mx-5 mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">电脑未连接。请保持 Langflow、Ollama 和「教材问答连接」运行；连接恢复后即可提问。</div>}
        <div className="flex-1 space-y-7 px-5 py-7 sm:px-7" aria-live="polite">
          {messages.length===0?<div className="mx-auto max-w-xl py-10"><div className="mb-5 inline-flex rounded-2xl bg-blue-50 p-3 text-[#173f8a]"><BookOpen size={28}/></div><h2 className="text-2xl font-bold">从教材中找到答案</h2><p className="mt-3 text-base leading-7 text-slate-500">输入一个完整问题，核对答案末尾的教材出处。</p><div className="mt-7 space-y-3">{suggestions.map(q=><button key={q} onClick={()=>setDraft(q)} className="block w-full rounded-xl border border-slate-200 px-4 py-3 text-left text-sm leading-6 text-slate-700 hover:border-blue-300 hover:bg-blue-50">{q}</button>)}</div></div>:messages.map(m=><div key={m.id} className="space-y-5"><div className="ml-auto max-w-[90%] rounded-2xl rounded-tr-sm bg-[#173f8a] px-5 py-3 text-base leading-7 whitespace-pre-wrap break-words text-white">{m.question}</div><div className="min-w-0 rounded-2xl border border-slate-100 bg-white p-1 sm:p-3"><div className="mb-3 flex items-center justify-between text-sm"><b className="flex items-center gap-2 text-[#173f8a]"><BookOpen size={17}/>教材助手</b>{m.status==='done'&&<div className="flex items-center gap-3 text-slate-400">{m.elapsed_ms!=null&&<span>{(m.elapsed_ms/1000).toFixed(1)} 秒</span>}<button onClick={()=>void copy(m.id,m.answer??'')} aria-label="复制答案" className="rounded p-1 hover:bg-slate-100">{copied===m.id?<Check size={16}/>:<Copy size={16}/>}</button></div>}</div>{m.status==='done'?<Answer text={m.answer??''}/>:m.status==='failed'?<div className="rounded-xl bg-red-50 p-4 text-sm text-red-800"><p>{m.error??'回答失败，请重试。'}</p><button disabled={!online||sending||pending} onClick={()=>void send(m.question)} className="mt-3 font-semibold underline disabled:opacity-40">重新提问</button></div>:<p className="flex items-center gap-2 py-3 text-sm text-slate-500"><LoaderCircle size={17} className="animate-spin"/>{m.status==='queued'?'等待电脑领取问题…':'正在检索教材并整理答案…'}</p>}</div></div>)}<div ref={end}/>
        </div>
        <form onSubmit={e=>{e.preventDefault();void send();}} className="sticky bottom-0 border-t border-slate-100 bg-white/95 px-5 py-4 backdrop-blur sm:px-7">{notice&&<p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{notice}</p>}<label htmlFor="textbook-question" className="sr-only">教材问题</label><div className="flex items-end gap-3 rounded-xl border border-slate-300 p-3 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100"><textarea id="textbook-question" maxLength={2000} rows={2} value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();void send();}}} placeholder="例如：MTBF 和 MTTR 有什么区别？请给出教材出处。" className="min-h-14 flex-1 resize-none bg-transparent text-base leading-7 outline-none"/><button type="submit" disabled={!online||sending||pending||!draft.trim()} aria-label="发送问题" className="rounded-lg bg-[#173f8a] p-3 text-white disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400">{sending?<LoaderCircle size={19} className="animate-spin"/>:<Send size={19}/>}</button></div><div className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-slate-400"><span>每次提问独立检索；追问请写全对象。Enter 发送，Shift+Enter 换行。</span><span>{draft.length}/2000</span></div></form>
      </section>
    </div>
  </main>;
}
