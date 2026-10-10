export type CritiquePoint={point:string;ranks:number[]};
export type CritiqueResult={summary:string;correct:CritiquePoint[];missing:CritiquePoint[];corrections:CritiquePoint[];suggestion:string;insufficientEvidence:boolean};
export type CritiqueJob={id:string;status:'queued'|'running'|'done'|'failed';result:CritiqueResult|null;error:string|null};
export function validateCritique(value:unknown,ranks:number[]):CritiqueResult{
  const fail=()=>{throw new Error('点评结果格式或引用无效。');};
  if(!value||typeof value!=='object')return fail();
  const v=value as Record<string,unknown>;
  const text=(s:unknown,max:number)=>{if(typeof s!=='string'||!s.trim()||s.length>max||/<\/?(?:think|script|iframe)\b/i.test(s))return fail();return s.trim();};
  const points=(list:unknown):CritiquePoint[]=>{
    if(!Array.isArray(list)||list.length>8)return fail();
    return list.map(p=>{if(!p||typeof p!=='object')return fail();const x=p as Record<string,unknown>;
      if(!Array.isArray(x.ranks)||!x.ranks.length||x.ranks.length>10||!x.ranks.every(r=>Number.isInteger(r)&&ranks.includes(r)))return fail();
      return {point:text(x.point,1500),ranks:[...new Set(x.ranks as number[])]};});
  };
  if(typeof v.insufficientEvidence!=='boolean')return fail();
  return {summary:text(v.summary,1500),correct:points(v.correct),missing:points(v.missing),corrections:points(v.corrections),suggestion:text(v.suggestion,1500),insufficientEvidence:v.insufficientEvidence};
}
