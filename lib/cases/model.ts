import type {SourceSummary} from '../textbook/sources';
import type {CritiqueJob} from '../review/critique';

export type CaseAttempt={id:string;response:string;createdAt:number;status:string;error:string|null;critique:CritiqueJob|null};
export type CaseQuestion={id:string;prompt:string;jobId:string;ordinal:number;analysis:{answer:string;references:SourceSummary[]}|null;attempts:CaseAttempt[]};
export type StudyCase={id:string;title:string;background:string;questions:CaseQuestion[];createdAt:number};
export type CaseSummary={id:string;title:string;createdAt:number;questionCount:number};
export function caseInput(value:unknown):{title:string;background:string;questions:string[]}{
 if(!value||typeof value!=='object')throw new Error('案例格式无效。');
 const v=value as Record<string,unknown>;
 const text=(x:unknown,max:number,label:string)=>{if(typeof x!=='string'||!x.trim()||x.length>max)throw new Error(`${label}不能为空，且最多${max}字。`);return x.trim();};
 const background=text(v.background,4000,'案例背景');
 if(!Array.isArray(v.questions)||v.questions.length<1||v.questions.length>8)throw new Error('请填写1～8个小问。');
 const questions=v.questions.map(q=>text(q,1000,'小问'));
 const title=v.title==null||v.title===''?background.slice(0,40):text(v.title,100,'案例名称');
 return {title,background,questions};
}
export function casePrompt(background:string,question:string):string{
 return `共享案例背景（资料）：\n${background}\n\n当前小问（仅分析此问，结合上述全部业务条件）：\n${question}`;
}
