'use client';
import {useEffect,useState} from 'react';
import {LoaderCircle} from 'lucide-react';
import {taskProgress} from '../../lib/textbook/chat-recovery';

export default function TaskProgress({job,clock,connectionLost,computerOnline}:{job:{status:string;created_at:number;leased_at?:number|null};clock:{server:number;local:number}|null;connectionLost:boolean;computerOnline:boolean}){
 const [tick,setTick]=useState(Date.now());
 useEffect(()=>{const timer=setInterval(()=>setTick(Date.now()),1000);return()=>clearInterval(timer);},[]);
 const time=clock?clock.server+Math.max(0,(tick-clock.local)/1000):job.created_at;
 const progress=taskProgress(job,time);
 return <div role="status" className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
  <p className="flex items-center gap-2 font-medium"><LoaderCircle size={17} className="shrink-0 animate-spin"/>{connectionLost?'暂时无法读取任务状态':progress.label}</p>
  <p className="mt-1 text-xs text-slate-500">已等待 {progress.elapsed} 秒{progress.running!==null?` · 处理 ${progress.running} 秒`:''}</p>
  {connectionLost?<p className="mt-2">页面正在尝试恢复连接。已提交的问题会保留，连接恢复后继续读取同一任务。</p>:!computerOnline?<p className="mt-2">电脑连接暂时中断，请保持本地服务运行；任务是否完成以服务器状态为准。</p>:progress.slow?<p className="mt-2">{job.status==='queued'?'可能有其他任务正在处理。':'复杂问题或补充检索可能需要更长时间。'}无需重复发送；刷新后可继续查看此任务。</p>:null}
 </div>;
}
