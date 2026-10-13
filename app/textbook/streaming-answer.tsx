'use client';
import {Square,LoaderCircle} from 'lucide-react';
export default function StreamingAnswer({job,busy,onStop}:{job:{status:string;partial_answer?:string|null;cancel_requested?:number};busy:boolean;onStop:()=>void}){
 const active=job.status==='queued'||job.status==='running',stopping=job.cancel_requested===1;
 return <div className="space-y-3">
  {job.partial_answer&&<><p className="text-xs text-amber-800">{active?'答案正在生成，正文与引用尚未完成校验。':'以下为已收到的未完成正文，尚未通过最终校验。'}</p><div className="whitespace-pre-wrap break-words text-base leading-7 text-slate-700">{job.partial_answer}</div></>}
  {job.status==='cancelled'&&<p role="status" className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">已停止。{job.partial_answer?'已保留收到的正文；这是未完成答案，可重新生成。':'未收到正文，可重新生成。'}</p>}
  {active&&<button type="button" disabled={busy||stopping} onClick={onStop} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50">{busy||stopping?<LoaderCircle size={13} className="animate-spin"/>:<Square size={13}/>} {stopping?'正在停止，等待本地确认…':busy?'正在发送停止请求…':'停止生成'}</button>}
 </div>;
}
