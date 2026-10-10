import type {SourceSummary} from '../textbook/sources';
import type {CritiqueJob} from './critique';

export type Grade='forgotten'|'partial'|'remembered';
export const GRADES:Record<Grade,string>={forgotten:'没记住',partial:'部分记住',remembered:'已记住'};
export type Favorite={id:string;job_id:string;question:string;retrieval_query:string|null;answer:string;created_at:number;references:SourceSummary[]};
export type ReviewCard={id:string;favorite_id:string;front:string;back:string;due_date:string;streak:number;version:number;job_id:string;references:SourceSummary[]};
export type ReviewRecord={id:string;card_id:string;grade:Grade;study_date:string;due_date:string;response:string;created_at:number;critique?:CritiqueJob|null};
export type ReviewData={favorites:Favorite[];cards:ReviewCard[];reviews:ReviewRecord[];today:string;stats:{study_date:string;cards:number;attempts:number}[]};

export function studyDate(date=new Date()):string {
  return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);
}
export function addDays(day:string,count:number):string {
  if(!/^\d{4}-\d{2}-\d{2}$/.test(day))throw new Error('日期无效。');
  const date=new Date(day+'T00:00:00Z');
  if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==day)throw new Error('日期无效。');
  date.setUTCDate(date.getUTCDate()+count);return date.toISOString().slice(0,10);
}
export function scheduleReview(streak:number,grade:unknown,today=studyDate()) {
  if(grade!=='forgotten'&&grade!=='partial'&&grade!=='remembered')throw new Error('请选择有效的自评等级。');
  const next=grade==='remembered'?Math.max(0,streak)+1:0;
  const interval=grade==='remembered'?[1,3,7,14][Math.min(next-1,3)]:1;
  return {streak:next,interval,dueDate:addDays(today,interval)};
}
export function cardText(value:unknown,max:number):string {
  if(typeof value!=='string'||!value.trim()||value.trim().length>max)throw new Error(`请填写内容，最多 ${max} 字。`);
  return value.trim();
}
export const planDays=()=>Array.from({length:40},(_,i)=>addDays('2026-09-15',i));
