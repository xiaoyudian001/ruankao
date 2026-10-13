export type AnswerAction='original'|'edit'|'regenerate';
export type RetrySource={id:string;action:'edit'|'regenerate'};
import type {EditorDraft} from './drafts';
const id=(v:unknown)=>typeof v==='string'&&/^[a-f0-9-]{36}$/i.test(v);
export function answerSelection(action:unknown,source:unknown):{action:AnswerAction;source:string|null}{
 if(action==null||action==='original'){if(source!=null)throw Error('回答操作与原问题标识不匹配。');return {action:'original',source:null};}
 if((action!=='edit'&&action!=='regenerate')||!id(source))throw Error('回答操作或原问题标识无效。');
 return {action,source:source as string};
}
export function sameAnswerAction(prior:{answer_action?:string|null;source_job_id?:string|null},next:{action:AnswerAction;source:string|null}){
 return (prior.answer_action??'original')===next.action&&(prior.source_job_id??null)===next.source;
}
export function originalHistory(raw:string):string{
 try{if(raw.length>20000)throw Error();const rows=JSON.parse(raw);if(!Array.isArray(rows)||rows.length>3||rows.some(r=>!r||typeof r.question!=='string'||typeof r.answer!=='string'||r.question.length>2000||r.answer.length>1000))throw Error();return raw;}catch{throw Error('原问题的上下文记录不可用，请作为新问题提问。');}
}
export function shouldConfirmEdit(current:EditorDraft,target:{id:string;question:string;retrieval_mode?:string;task_type?:string;screenshotId?:string|null}):boolean{
 const hasDraft=Boolean(current.text.trim()||current.screenshot||current.retrySource);
 const unchanged=current.retrySource?.id===target.id&&current.text===target.question&&current.mode===(target.retrieval_mode??'default')&&current.taskType===(target.task_type??'qa')&&(current.screenshot?.id??null)===(target.screenshotId??null);
 return hasDraft&&!unchanged;
}
