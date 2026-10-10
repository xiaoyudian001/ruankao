'use client';
import {useEffect,useRef,useState} from 'react';
import {LoaderCircle,Sparkles} from 'lucide-react';
import type {CritiqueJob,CritiqueResult} from '../../lib/review/critique';
import type {ReviewCard} from '../../lib/review/model';

export function CritiqueDetails({result,onCitation}:{result:CritiqueResult;onCitation:(rank:number)=>void}){
 return <div className="space-y-4 text-sm leading-7">
  <p className="whitespace-pre-wrap font-medium text-slate-800">{result.summary}</p>
  {result.insufficientEvidence&&<p className="rounded-lg bg-amber-50 p-3 text-amber-800">当前教材片段不足以完整判断，请结合原页核对。</p>}
  {([['correct','已答对'],['missing','遗漏要点'],['corrections','需要纠正']] as const).map(([key,label])=><section key={key}><h4 className="font-semibold text-[#173f8a]">{label}</h4>{result[key].length?<ul className="mt-1 space-y-2">{result[key].map((p,i)=><li key={i} className="whitespace-pre-wrap">{p.point} <span className="inline-flex flex-wrap gap-1">{p.ranks.map(rank=><button key={rank} onClick={()=>onCitation(rank)} className="rounded-md bg-blue-100 px-2 text-xs font-medium text-blue-800 hover:bg-blue-200" aria-label={`查看点评依据片段${rank}`}>[片段{rank}]</button>)}</span></li>)}</ul>:<p className="text-slate-500">{key==='correct'?'本次未识别到已掌握要点。':key==='missing'?'未发现需要补充的要点。':'未发现明确错误。'}</p>}</section>)}
  <p className="whitespace-pre-wrap rounded-lg bg-white p-3 text-slate-700"><b>下一次怎么练：</b>{result.suggestion}</p>
 </div>;
}

export default function CritiquePanel({card,response,initialId,onJob,onSubmitting,onCitation}:{card:ReviewCard;response:string;initialId:string|null;onJob:(id:string)=>void;onSubmitting:(busy:boolean)=>void;onCitation:(rank:number)=>void}){
 const [job,setJob]=useState<CritiqueJob|null>(initialId?{id:initialId,status:'running',result:null,error:null}:null),[error,setError]=useState(''),[submitting,setSubmitting]=useState(false);
 const requestId=useRef<string|null>(null),jobCallback=useRef(onJob);jobCallback.current=onJob;
 const mounted=useRef(true);useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{
  if(!job||!['queued','running'].includes(job.status))return;
  let active=true,timer:ReturnType<typeof setTimeout>;const abort=new AbortController();
  async function poll(){try{const r=await fetch('/api/textbook/critique?id='+job!.id,{cache:'no-store',signal:abort.signal});const d=await r.json() as {critique:CritiqueJob;error?:string};if(!r.ok)throw new Error(d.error??'暂时无法读取点评。');if(active){setError('');setJob(d.critique);}}catch(e){if(active)setError(e instanceof Error?e.message:'连接暂时中断。');}finally{if(active)timer=setTimeout(poll,2000);}}
  timer=setTimeout(poll,1000);return()=>{active=false;abort.abort();clearTimeout(timer);};
 },[job?.id,job?.status]);
 async function submit(){
  if(submitting)return;setSubmitting(true);onSubmitting(true);setError('');
  if(!requestId.current||job?.status==='failed')requestId.current=crypto.randomUUID();
  try{const r=await fetch('/api/textbook/critique',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(15000),body:JSON.stringify({requestId:requestId.current,cardId:card.id,version:card.version,response})});const d=await r.json() as {critique:CritiqueJob;error?:string};if(!r.ok)throw new Error(d.error??'点评提交失败。');if(mounted.current){setJob(d.critique);jobCallback.current(d.critique.id);}}
  catch(e){if(mounted.current)setError(e instanceof Error?e.message:'点评提交失败。');}finally{if(mounted.current){setSubmitting(false);onSubmitting(false);}}
 }
 const pending=job&&['queued','running'].includes(job.status);
 return <section className="mt-5 rounded-xl border border-blue-100 bg-blue-50/60 p-5" aria-label="AI 回忆点评">
  <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="flex items-center gap-2 font-semibold text-[#173f8a]"><Sparkles size={17}/>AI 点评 <span className="text-xs font-normal text-slate-500">MiniMax-M3</span></h3>
   {job?.status!=='done'&&<button onClick={()=>void submit()} disabled={Boolean(pending)||submitting} className="flex items-center gap-2 rounded-lg bg-[#173f8a] px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{pending||submitting?<LoaderCircle size={15} className="animate-spin"/>:<Sparkles size={15}/>} {pending?'正在核对教材…':submitting?'正在提交…':job?.status==='failed'?'重新点评':'点评我的回忆'}</button>}</div>
  <p className="mb-4 mt-2 text-xs leading-6 text-slate-500">对照已保存的教材片段核对；电脑连接时可用。AI 点评辅助理解，复习日期由你的自评决定。</p>
  {(error||job?.error)&&<p role="alert" className="mb-3 text-sm text-amber-800">{error||job?.error} 可以继续下方自评。</p>}
  {job?.result&&<CritiqueDetails result={job.result} onCitation={onCitation}/>}
  {pending&&<p role="status" className="text-sm text-blue-800">{job.status==='queued'?'正在等待本机领取任务。':'MiniMax 正在对照教材核对要点。'}你可以先完成自评，稍后在练习记录中查看。</p>}
 </section>;
}
