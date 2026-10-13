// This tab remembers navigation and uncertain submissions, never answers or credentials.
import type {RetrievalMode} from './policy';
import type {TaskType} from './exam';

export type PendingRequest={question:string;sessionId:string|null;id:string;mode:RetrievalMode;taskType:TaskType;screenshotId:string|null};
export type Recovery={sessionId:string|null;request:PendingRequest|null};
type StorageAccess=Pick<Storage,'getItem'|'setItem'|'removeItem'>;
const id=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9-]{36}$/i.test(v);
const nullableId=(v:unknown)=>v===null||id(v);
const key=(owner:string)=>'textbook-chat-recovery-v1:'+owner;

export function saveRecovery(storage:StorageAccess,owner:string,value:Recovery,time=Date.now()):void {
 try{storage.setItem(key(owner),JSON.stringify({...value,savedAt:time}));}catch{/* Restricted storage must not prevent online use. */}
}
export function loadRecovery(storage:StorageAccess,owner:string,time=Date.now()):Recovery|null {
 try{
  const raw=storage.getItem(key(owner));if(!raw)return null;
  const value=JSON.parse(raw);
  if(!value||!Number.isFinite(value.savedAt)||time-value.savedAt>86400000||time<value.savedAt||!nullableId(value.sessionId))return null;
  const r=value.request;
  if(r!==null&&(!r||!id(r.id)||!nullableId(r.sessionId)||!nullableId(r.screenshotId)||typeof r.question!=='string'||!r.question.trim()||r.question.length>2000||!['default','complete'].includes(r.mode)||!['qa','exam'].includes(r.taskType)||(r.screenshotId!==null&&r.taskType!=='exam')))return null;
  return {sessionId:value.sessionId,request:r===null?null:{id:r.id,sessionId:r.sessionId,question:r.question,mode:r.mode,taskType:r.taskType,screenshotId:r.screenshotId}};
 }catch{return null;}
}

/** Only one read per selection; a new selection invalidates all old responses. */
export class ChatReader<T> {
 private active:{key:string;controller:AbortController}|null=null;
 private timeoutMs:number;
 constructor(timeoutMs=12000){this.timeoutMs=timeoutMs;}
 cancel(){this.active?.controller.abort();this.active=null;}
 async read(key:string,operation:(signal:AbortSignal)=>Promise<T>):Promise<T|null>{
  if(this.active?.key===key)return null;
  this.cancel();const current={key,controller:new AbortController()};this.active=current;
  let timer:ReturnType<typeof setTimeout>|undefined;
  let timedOut=false;
  const aborted=new Promise<never>((_,reject)=>current.controller.signal.addEventListener('abort',()=>reject(new Error(timedOut?'读取超时，正在尝试恢复连接。':'读取已取消。')),{once:true}));
  timer=setTimeout(()=>{timedOut=true;current.controller.abort();},this.timeoutMs);
  try{
   const value=await Promise.race([operation(current.controller.signal),aborted]);
   return this.active===current?value:null;
  }catch(e){if(this.active!==current)return null;throw e;}
  finally{clearTimeout(timer);if(this.active===current)this.active=null;}
 }
}

export function taskProgress(job:{status:string;created_at:number;leased_at?:number|null},time:number){
 const elapsed=Math.max(0,Math.floor(time-job.created_at));
 const running=job.status==='running'&&typeof job.leased_at==='number'?Math.max(0,Math.floor(time-job.leased_at)):null;
 return {label:job.status==='queued'?'已排队，等待电脑领取':'电脑正在处理问题',elapsed,running,slow:job.status==='queued'?elapsed>=30:running!==null&&running>=60};
}
