import type {TokenUsage} from '../../lib/textbook/token-usage';

export default function AnswerUsage({usage}:{usage?:TokenUsage|null}){
 if(!usage||usage.reportedCalls===0)return <span className="text-xs text-slate-400">Token 用量未提供</span>;
 const n=(value:number|null)=>value==null?'未提供':value.toLocaleString('en-US');
 return <details className="relative text-xs text-slate-500">
  <summary className="cursor-pointer rounded px-1 py-0.5 hover:bg-slate-50" aria-label="展开答案生成 Token 用量">输入 {n(usage.inputTokens)} · 输出 {n(usage.outputTokens)} Token{usage.unreportedCalls>0?'（部分）':''}</summary>
  <div className="absolute right-0 z-20 mt-2 w-72 max-w-[80vw] rounded-xl border border-slate-200 bg-white p-3 text-left leading-6 text-slate-600 shadow-lg">
   <p className="font-semibold">{usage.unreportedCalls>0?'部分调用用量':'答案生成用量'}</p>
   <p>输入 {n(usage.inputTokens)} · 输出 {n(usage.outputTokens)} · 合计 {n(usage.totalTokens)} Token</p>
   <p>模型：{usage.models.join('、')||'未提供'}</p>
   <p>已统计 {usage.reportedCalls} 次答案生成调用，包含已获取用量的格式重试和图文回退。</p>
   {usage.unreportedCalls>0&&<p>至少 {usage.unreportedCalls} 次调用未取得统计，以上仅为已知用量。</p>}
   <p className="mt-1 text-slate-400">不包含问题重写、检索规划、证据判断和向量化。输出按模型服务统计，可能包含推理 Token。</p>
  </div>
 </details>;
}
