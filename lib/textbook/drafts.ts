import type {RetrievalMode} from './policy';
import type {TaskType} from './exam';
export type Draft={text:string;mode:RetrievalMode;taskType:TaskType;screenshot:{id:string;confirmed:boolean}|null};
type StorageAccess=Pick<Storage,'getItem'|'setItem'|'removeItem'>;
const key=(owner:string,session:string|null)=>'textbook-draft-v1:'+owner+':'+(session??'new');
const id=(v:unknown)=>typeof v==='string'&&/^[a-f0-9-]{36}$/i.test(v);
export const emptyDraft=():Draft=>({text:'',mode:'default',taskType:'qa',screenshot:null});
function normalize(value:unknown):Draft|null{
 if(!value||typeof value!=='object')return null;const d=value as Record<string,unknown>;
 if(typeof d.text!=='string'||d.text.length>2000||typeof d.mode!=='string'||!['default','complete'].includes(d.mode)||typeof d.taskType!=='string'||!['qa','exam'].includes(d.taskType))return null;
 const s=d.screenshot as {id?:unknown;confirmed?:unknown}|null;
 if(s&&s.id!=null&&(!id(s.id)||typeof s.confirmed!=='boolean'))return null;
 return {text:d.text,mode:d.mode as RetrievalMode,taskType:d.taskType as TaskType,screenshot:d.taskType==='exam'&&s&&id(s.id)?{id:s.id as string,confirmed:s.confirmed as boolean}:null};
}
export function saveDraft(storage:StorageAccess,owner:string,session:string|null,value:unknown,time=Date.now()):boolean{
 const draft=normalize(value);if(!draft)return false;
 try{storage.setItem(key(owner,session),JSON.stringify({...draft,savedAt:time}));return true;}catch{return false;}
}
export function loadDraft(storage:StorageAccess,owner:string,session:string|null,time=Date.now()):Draft|null{
 try{const raw=storage.getItem(key(owner,session));if(!raw)return null;const d=JSON.parse(raw);
 if(!Number.isFinite(d?.savedAt)||time<d.savedAt||time-d.savedAt>30*86400000)return null;
 return normalize(d);
 }catch{return null;}
}
export function removeDraft(storage:StorageAccess,owner:string,session:string|null):boolean{
 try{storage.removeItem(key(owner,session));return true;}catch{return false;}
}
export function clearSubmittedDraft(storage:StorageAccess,owner:string,session:string|null,submitted:Draft):boolean{
 try{const raw=storage.getItem(key(owner,session));if(!raw)return false;const d=normalize(JSON.parse(raw));
 if(!d||d.text.trim()!==submitted.text.trim()||d.mode!==submitted.mode||d.taskType!==submitted.taskType||d.screenshot?.id!==submitted.screenshot?.id)return false;
 return removeDraft(storage,owner,session);
 }catch{return false;}
}

export type EditorDraft=Omit<Draft,'screenshot'>&{screenshot:{id:string|null;confirmed:boolean}|null};
export class DraftWorkspace {
 value:EditorDraft=emptyDraft();sessionId:string|null=null;status='';
 private storage:StorageAccess;private owner:string;
 constructor(storage:StorageAccess,owner:string){this.storage=storage;this.owner=owner;}
 open(session:string|null,override?:EditorDraft){
  this.sessionId=session;const saved=loadDraft(this.storage,this.owner,session);this.value=override??saved??emptyDraft();
  this.status=saved?'已恢复此会话的草稿与设置':'';
 }
 update(change:Partial<EditorDraft>){
  this.value={...this.value,...change};this.status=saveDraft(this.storage,this.owner,this.sessionId,this.value)?'草稿和设置已保存到此浏览器':'浏览器无法保存草稿，请保留页面或复制文字。';
 }
 clear(){this.value=emptyDraft();this.status=removeDraft(this.storage,this.owner,this.sessionId)?'草稿已清空':'草稿未能清除，请检查浏览器存储设置。';}
 complete(source:string|null,target:string|null,submitted:Draft){
  const removed=clearSubmittedDraft(this.storage,this.owner,source,submitted);
  if(this.sessionId!==source)return;
  const later=loadDraft(this.storage,this.owner,target);
  const memoryChanged=this.value.text.trim()!==submitted.text.trim()||this.value.mode!==submitted.mode||this.value.taskType!==submitted.taskType||this.value.screenshot?.id!==submitted.screenshot?.id;
  this.sessionId=target;this.value=later??(memoryChanged?this.value:{text:'',mode:submitted.mode,taskType:submitted.taskType,screenshot:null});
  this.status=later||memoryChanged?'已保留尚未发送的草稿':removed?'已发送，对应草稿已清除':'';
  if(memoryChanged&&!later&&!saveDraft(this.storage,this.owner,target,this.value))this.status='浏览器无法保存草稿，请保留页面或复制文字。';
 }
}
