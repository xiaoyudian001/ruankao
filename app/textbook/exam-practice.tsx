'use client';

import {useEffect,useState} from 'react';
import {LoaderCircle} from 'lucide-react';
import Answer from './answer';
import type {PracticeView} from '../../lib/textbook/exam';

export default function ExamPractice({jobId,practice,onSubmitted,onCitation,citationRanks}:{jobId:string;practice:PracticeView;onSubmitted:()=>void;onCitation:(rank:number)=>void;citationRanks:number[]}){
 const [view,setView]=useState(practice),[choice,setChoice]=useState(practice.choice??''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{if(practice.choice){setView(practice);setChoice(practice.choice);}},[practice]);
 const submitted=Boolean(view.choice);
 async function submit(){
  if(!choice||busy||submitted)return;setBusy(true);setError('');
  try{
   const r=await fetch('/api/textbook/exam',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jobId,choice})});
   const data=await r.json() as {error?:string;practice:PracticeView};
   if(!r.ok)throw new Error(data.error??'提交失败，请重试。');
   setView(data.practice);setChoice(data.practice.choice??choice);onSubmitted();
  }catch(e){setError(e instanceof Error?e.message:'提交失败，请重试。');onSubmitted();}
  finally{setBusy(false);}
 }
 return <section className="mt-6 rounded-xl border border-blue-100 bg-[#f5f8ff] p-4 sm:p-5" aria-label="类似练习">
  <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold text-[#173f8a]">练一道类似题</h3><span className="text-xs text-slate-500">AI 辅助练习 · 单选 · 非历年真题</span></div>
  <p className="mt-3 whitespace-pre-wrap text-base leading-7 text-slate-800">{view.question}</p>
  <fieldset disabled={busy||submitted} className="mt-4 space-y-2"><legend className="sr-only">请选择一个选项</legend>{view.options.map(o=><label key={o.label} className={`flex cursor-pointer items-start gap-3 rounded-lg border bg-white p-3 text-sm leading-6 ${choice===o.label?'border-blue-600 text-[#173f8a]':'border-slate-200 text-slate-700'} ${submitted?'cursor-default':''}`}><input type="radio" name={'practice-'+jobId} value={o.label} checked={choice===o.label} onChange={()=>setChoice(o.label)} className="mt-1.5 accent-blue-800"/><span className="whitespace-pre-wrap"><b>{o.label}.</b> {o.text}</span></label>)}</fieldset>
  {!submitted?<div className="mt-4 flex flex-wrap items-center gap-3"><button type="button" disabled={!choice||busy} onClick={()=>void submit()} className="flex items-center gap-2 rounded-lg bg-[#173f8a] px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{busy&&<LoaderCircle size={16} className="animate-spin"/>}提交并查看解析</button><span className="text-xs text-slate-500">先选答案，再对照解析。</span></div>:<div className="mt-5 border-t border-blue-100 pt-4" aria-live="polite"><p className={`font-semibold ${view.isCorrect?'text-emerald-700':'text-amber-800'}`}>{view.isCorrect?'回答正确':'本题需要再巩固'} · 你选了 {view.choice}，参考答案 {view.correct}</p><div className="mt-3"><Answer text={view.explanation??''} citationRanks={citationRanks} onCitation={onCitation}/></div><p className="mt-3 text-sm text-slate-600">练习依据：{view.ranks?.map(rank=><button key={rank} type="button" onClick={()=>onCitation(rank)} className="ml-2 rounded bg-blue-50 px-1 font-medium text-[#173f8a] underline">[片段{rank}]</button>)}</p></div>}
  {error&&<p role="alert" className="mt-3 text-sm text-red-800">{error}</p>}
 </section>;
}
