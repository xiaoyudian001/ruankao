'use client';
import {useEffect,useState} from 'react';
import {Brain,ChevronRight} from 'lucide-react';

export default function TodayReview(){
  const [counts,setCounts]=useState<{due:number;done:number;cards:number}|null>(null);
  useEffect(()=>{const c=new AbortController();void fetch('/api/textbook/review?view=summary',{signal:c.signal,cache:'no-store'}).then(async r=>{if(!r.ok)return;const d=await r.json() as {due:number;done:number;cards:number};setCounts(d);}).catch(()=>{});return()=>c.abort();},[]);
  return <section className="mb-5 flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-blue-200 bg-white p-5 sm:p-6"><div className="flex items-center gap-4"><span className="rounded-xl bg-blue-50 p-3 text-[#173f8a]"><Brain size={24}/></span><div><h3 className="font-bold">今日主动回忆</h3><p className="mt-1 text-sm leading-6 text-slate-500">{counts?`待练 ${counts.due} 张 · 已练 ${counts.done} 张 · 共 ${counts.cards} 张卡片`:'收藏教材答案，制作卡片，逐步安排到复习计划。'}</p></div></div><a href="/review?tab=practice" className="inline-flex items-center gap-2 rounded-xl bg-[#173f8a] px-4 py-2.5 text-sm font-semibold text-white">进入复习中心<ChevronRight size={16}/></a></section>;
}
