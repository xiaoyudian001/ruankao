'use client';

import {useEffect,useRef,useState} from 'react';
import {ArrowRight,BookOpen,Check,ChevronRight,GitFork,Layers,PenLine,X} from 'lucide-react';
import Answer from '../textbook/answer';
import {CASE,ESSAY,QUESTION,SOURCES,type DemoSourceData} from '../../lib/demo/content';

type Scenario='question'|'case'|'essay';
type ExampleProps={onCitation:(rank:number)=>void};
type DraftProps=ExampleProps & {revision:0|1;revealed:boolean;onChoose:(revision:0|1)=>void;onSubmit:()=>void};
const scenarios=[{id:'question',number:'01',title:'教材问答',detail:'追溯每个结论',Icon:BookOpen},{id:'case',number:'02',title:'案例练习',detail:'先作答，再核对',Icon:Layers},{id:'essay',number:'03',title:'论文训练',detail:'让修改有依据',Icon:PenLine}] as const;
const focus='focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-700';

function Label({children}:{children:React.ReactNode}){return <p className="mb-3 text-xs font-semibold tracking-wider text-slate-500">{children}</p>;}
function Feedback({text,onCitation}:ExampleProps & {text:string}){
  return <section className="mt-6 rounded-2xl border border-blue-100 bg-white p-5 sm:p-6" aria-label="预录反馈">
    <div className="mb-5 flex flex-wrap items-center justify-between gap-2"><span className="flex items-center gap-2 font-semibold text-[#173f8a]"><BookOpen size={17}/>学习助手</span><span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500">预录结果 · 非实时生成</span></div>
    <Answer text={text} onCitation={onCitation} citationRanks={SOURCES.map(x=>x.rank)}/>
    <p className="mt-5 border-t border-slate-100 pt-4 text-xs leading-6 text-slate-500">点蓝色片段引用，查看自写原页。演示页码与真实教材页码无关。</p>
  </section>;
}
function DraftSelector({revision,onChoose,labels}:{revision:0|1;onChoose:(revision:0|1)=>void;labels:string[]}){
  return <div className="mb-4 flex flex-wrap gap-2" aria-label="选择示例稿">
    {labels.map((label,i)=><button key={label} type="button" aria-pressed={revision===i} onClick={()=>onChoose(i as 0|1)} className={`rounded-lg border px-3 py-2 text-sm font-medium ${focus} ${revision===i?'border-[#173f8a] bg-[#173f8a] text-white':'border-slate-200 bg-white text-slate-600 hover:border-blue-300'}`}>{label}</button>)}
  </div>;
}

export function QuestionExample({onCitation}:ExampleProps){return <>
  <Label>你问</Label><h3 className="text-xl font-semibold leading-8">{QUESTION.question}</h3>
  <Feedback text={QUESTION.answer} onCitation={onCitation}/>
</>;}

export function CaseExample({onCitation,revision,revealed,onChoose,onSubmit}:DraftProps){return <>
  <Label>共享背景 · 合成案例</Label><p className="rounded-xl border-l-4 border-amber-300 bg-amber-50/60 p-4 text-sm leading-7 text-slate-700">{CASE.background}</p>
  <h3 className="my-5 text-lg font-semibold leading-8">{CASE.question}</h3>
  <Label>选择一份示例答案，先读完再提交</Label>
  <DraftSelector revision={revision} onChoose={onChoose} labels={CASE.drafts.map(x=>x.label)}/>
  <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-7">{CASE.drafts[revision].answer}</p>
  <button type="button" onClick={onSubmit} disabled={revealed} className={`mt-4 inline-flex items-center gap-2 rounded-xl bg-[#173f8a] px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-200 disabled:text-slate-600 ${focus}`}>{revealed?<><Check size={16}/>已显示对应点评</>:<>提交示例答案<ArrowRight size={16}/></>}</button>
  <p className="mt-2 text-xs leading-6 text-slate-500">演示支持两份固定答案。切换到补充稿，再提交即可比较点评。</p>
  {revealed&&<Feedback text={CASE.drafts[revision].feedback} onCitation={onCitation}/>}
</>;}

export function EssayExample({onCitation,revision,revealed,onChoose,onSubmit,outlineVisible,onOutline}:DraftProps & {outlineVisible:boolean;onOutline:()=>void}){return <>
  <Label>论文题目 · 合成项目</Label><h3 className="text-xl font-semibold leading-8">{ESSAY.topic}</h3>
  <p className="my-4 rounded-xl border-l-4 border-amber-300 bg-amber-50/60 p-4 text-sm leading-7 text-slate-700">{ESSAY.facts}</p>
  <button type="button" onClick={onOutline} aria-expanded={outlineVisible} className={`mb-5 flex items-center gap-2 text-sm font-semibold text-[#173f8a] underline underline-offset-4 ${focus}`}>{outlineVisible?'收起示例提纲':'查看示例提纲'}<ChevronRight size={16}/></button>
  {outlineVisible&&<section className="mb-6 rounded-xl border border-blue-100 bg-blue-50/40 p-5" aria-label="示例提纲"><Answer text={ESSAY.outline} onCitation={onCitation} citationRanks={[1,3]}/></section>}
  <Label>架构方案段落 · 比较两份稿件</Label>
  <DraftSelector revision={revision} onChoose={onChoose} labels={ESSAY.drafts.map(x=>x.label)}/>
  <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-7">{ESSAY.drafts[revision].answer}</p>
  <button type="button" onClick={onSubmit} disabled={revealed} className={`mt-4 inline-flex items-center gap-2 rounded-xl bg-[#173f8a] px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-200 disabled:text-slate-600 ${focus}`}>{revealed?<><Check size={16}/>已显示本稿点评</>:<>查看本稿预录点评<ArrowRight size={16}/></>}</button>
  <p className="mt-2 text-xs leading-6 text-slate-500">初稿与修改稿分别对应独立点评；合成经历不能用于冒充真实项目。</p>
  {revealed&&<Feedback text={ESSAY.drafts[revision].feedback} onCitation={onCitation}/>}
</>;}

export function DemoSource({source,onClose}:{source:DemoSourceData;onClose:()=>void}){
  const title=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{title.current?.focus();},[source.rank]);
  return <aside className="h-fit rounded-2xl border border-slate-200 bg-[#eef2f7] p-3 sm:p-5 xl:sticky xl:top-6" aria-labelledby="demo-source-heading">
    <div className="mb-4 flex items-center justify-between gap-3"><h3 id="demo-source-heading" ref={title} tabIndex={-1} className={`text-sm font-semibold text-[#173f8a] ${focus}`}>片段{source.rank} · 查看自写原页</h3><button type="button" onClick={onClose} className={`inline-flex items-center gap-1 rounded-lg bg-white px-3 py-2 text-xs font-medium ${focus}`}><X size={14}/>返回演示</button></div>
    <article className="border border-slate-200 bg-[#fffefa] p-5 shadow-sm sm:p-7">
      <div className="mb-7 flex items-center justify-between border-b border-slate-200 pb-3 text-xs text-slate-500"><span>自写学习笔记 · 公开演示资料</span><span>第 {source.page} 页</span></div>
      <Answer text={source.text}/>
      <p className="mt-8 border-t border-slate-200 pt-3 text-xs leading-6 text-slate-500">此页由项目作者为演示编写，不是《系统架构设计师教程》的扫描页或摘录。</p>
    </article>
  </aside>;
}

export default function DemoWorkspace(){
  const [scenario,setScenario]=useState<Scenario>('question');
  const [caseRevision,setCaseRevision]=useState<0|1>(0);const [caseRevealed,setCaseRevealed]=useState(false);
  const [essayRevision,setEssayRevision]=useState<0|1>(0);const [essayRevealed,setEssayRevealed]=useState(false);const [outlineVisible,setOutlineVisible]=useState(false);
  const [source,setSource]=useState<DemoSourceData|null>(null);const trigger=useRef<HTMLElement|null>(null);
  function cite(rank:number){const next=SOURCES.find(x=>x.rank===rank);if(next){trigger.current=document.activeElement instanceof HTMLElement?document.activeElement:null;setSource(next);}}
  function closeSource(){setSource(null);trigger.current?.focus();}
  useEffect(()=>{if(!source)return;const handle=(event:KeyboardEvent)=>{if(event.key==='Escape'){setSource(null);trigger.current?.focus();}};window.addEventListener('keydown',handle);return()=>window.removeEventListener('keydown',handle);},[source]);
  return <main className="min-h-screen bg-[#f4f7fb] text-slate-950">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
      <a href="/demo" className={`flex items-center gap-3 ${focus}`}><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#173f8a] text-white"><BookOpen size={21}/></span><span><b className="block text-sm">软考 AI 学习助手</b><span className="text-xs text-slate-500">公开演示</span></span></a>
      <nav aria-label="项目导航" className="flex gap-5 text-sm"><a href="https://github.com/xiaoyudian001/ruankao" target="_blank" rel="noreferrer" className={`flex items-center gap-2 font-semibold text-[#173f8a] ${focus}`}><GitFork size={17}/>GitHub</a><a href="/" className={`text-slate-600 ${focus}`}>个人学习台<span className="sr-only">，仅所有者可用的学习功能</span></a></nav>
    </div></header>
    <div className="mx-auto max-w-7xl px-5 pb-12 pt-10 sm:px-8 sm:pt-14">
      <section className="mb-10 grid items-end gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div><p className="mb-4 text-xs font-semibold tracking-[.16em] text-[#173f8a]">教材溯源 / 案例练习 / 论文训练</p><h1 style={{fontFamily:'"Noto Serif SC", "Songti SC", SimSun, serif'}} className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">读懂答案。<br/>也看清它的依据。</h1><p className="mt-5 max-w-xl text-base leading-8 text-slate-600">从一次问答，到自己作答，再到修改稿件。用三个完整场景，体验有来源的 AI 学习过程。</p></div>
        <div className="border-l-2 border-[#173f8a] pl-5"><p className="mb-2 text-sm font-semibold">无需登录 · 电脑离线也可查看</p><p className="text-sm leading-7 text-slate-600">这是预录演示，使用自写学习笔记与合成项目。点击、比较、核对均可体验；结果不由模型实时生成。</p></div>
      </section>
      <div className="mb-6 grid gap-2 sm:grid-cols-3" aria-label="选择演示场景">
        {scenarios.map(({id,number,title,detail,Icon})=><button key={id} type="button" aria-pressed={scenario===id} onClick={()=>{setScenario(id);setSource(null);}} className={`flex items-center gap-3 rounded-xl border p-4 text-left transition-colors ${focus} ${scenario===id?'border-[#173f8a] bg-[#173f8a] text-white':'border-slate-200 bg-white hover:border-blue-300'}`}><span className={`text-xs font-semibold ${scenario===id?'text-blue-200':'text-slate-400'}`}>{number}</span><Icon size={20}/><span><b className="block text-sm">{title}</b><span className={`text-xs ${scenario===id?'text-blue-200':'text-slate-500'}`}>{detail}</span></span></button>)}
      </div>
      <div className={`grid items-start gap-5 ${source?'xl:grid-cols-[1.15fr_1fr]':'lg:grid-cols-[1fr_.42fr]'}`}>
        <section className="min-w-0 rounded-2xl border border-slate-200 bg-slate-50/70 p-5 sm:p-7" aria-label="演示内容">
          {scenario==='question'?<QuestionExample onCitation={cite}/>:scenario==='case'?<CaseExample onCitation={cite} revision={caseRevision} revealed={caseRevealed} onChoose={value=>{setCaseRevision(value);setCaseRevealed(false);}} onSubmit={()=>setCaseRevealed(true)}/>:<EssayExample onCitation={cite} revision={essayRevision} revealed={essayRevealed} onChoose={value=>{setEssayRevision(value);setEssayRevealed(false);}} onSubmit={()=>setEssayRevealed(true)} outlineVisible={outlineVisible} onOutline={()=>setOutlineVisible(value=>!value)}/>}
        </section>
        {source?<DemoSource source={source} onClose={closeSource}/>:<aside className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6">
          <Label>这一场景，试着做什么</Label>
          <h2 className="text-lg font-bold">{scenario==='question'?'追溯结论':scenario==='case'?'把遗漏补完整':'把工程理由写清楚'}</h2>
          <p className="text-sm leading-7 text-slate-600">{scenario==='question'?'点击回答中的蓝色引用，在旁边核对支撑结论的原页。原页打开后，问答仍可阅读。':scenario==='case'?'提交初次作答，读完反馈。再选择补充后的示例答案，查看点评有什么变化。':'展开提纲，再分别查看初稿与修改稿的点评。注意哪些说法缺少事实依据。'}</p>
          <div className="border-t border-slate-100 pt-4 text-xs leading-6 text-slate-500">真实实例使用你自备的教材，引用可打开原 PDF 页。演示使用自写笔记，便于公开分享。</div>
        </aside>}
      </div>
      <section className="mt-10 flex flex-wrap items-center justify-between gap-5 border-t border-slate-200 pt-7"><div><h2 className="font-semibold">想在自己的资料上使用？</h2><p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">项目提供网页、本机连接器和 RAG 源码。实时功能需要自行配置服务；当前在线学习空间仅供网站所有者使用。</p></div><a href="https://github.com/xiaoyudian001/ruankao#快速开始" target="_blank" rel="noreferrer" className={`inline-flex items-center gap-2 rounded-xl border border-[#173f8a] bg-white px-5 py-3 text-sm font-semibold text-[#173f8a] hover:bg-blue-50 ${focus}`}>查看源码与运行说明<ArrowRight size={17}/></a></section>
      <footer className="mt-8 flex flex-wrap justify-between gap-3 text-xs text-slate-500"><span>自写资料 · 预录点评 · 不提供官方评分</span><a href="https://github.com/xiaoyudian001/ruankao/issues" target="_blank" rel="noreferrer" className={`underline underline-offset-4 ${focus}`}>反馈问题</a></footer>
    </div>
  </main>;
}
