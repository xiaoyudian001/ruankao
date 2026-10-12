import {bridgeState,database,expireJobs,json,now,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {sourceSummaries} from '../../../../lib/textbook/sources';
import {essayInput,essayTask,type Essay,type EssayInput,type EssayRun} from '../../../../lib/essays/model';

const fields=(row:Record<string,unknown>):EssayInput=>essayInput({title:row.title,topic:row.topic,requirements:row.requirements,projectFacts:row.project_facts,drafts:JSON.parse(String(row.drafts_json))});
async function readEssay(id:string,userId:string):Promise<Essay|null>{
 const db=database(),row=await db.prepare('SELECT * FROM textbook_essays WHERE id=? AND owner_id=?').bind(id,userId).first();if(!row)return null;
 const runs=await db.prepare('SELECT r.*,j.status,j.answer,j.error,j.references_json FROM textbook_essay_runs r JOIN textbook_jobs j ON j.id=r.id AND j.owner_id=r.owner_id WHERE r.essay_id=? AND r.owner_id=? ORDER BY r.created_at DESC,r.rowid DESC LIMIT 50').bind(id,userId).all();
 return {...fields(row),id:String(row.id),version:Number(row.version),updatedAt:Number(row.updated_at),runs:runs.results.map(r=>{
  const p=JSON.parse(String(r.payload_json));return {id:String(r.id),kind:r.kind as EssayRun['kind'],section:String(r.section),draft:p.draft,projectFacts:p.projectFacts,topic:p.topic,requirements:p.requirements,version:Number(r.essay_version),status:String(r.status),answer:typeof r.answer==='string'?r.answer:null,error:typeof r.error==='string'?r.error:null,references:sourceSummaries(r.references_json),createdAt:Number(r.created_at)};
 })};
}
export async function GET(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);await expireJobs();
  const list=await database().prepare('SELECT id,title,topic,updated_at AS updatedAt FROM textbook_essays WHERE owner_id=? ORDER BY updated_at DESC,rowid DESC LIMIT 50').bind(user.userId).all(),connection=await bridgeState();
  const id=new URL(request.url).searchParams.get('id');if(!id)return json({essays:list.results,ready:connection.essayReady===true,online:connection.online});
  if(!validId(id))return json({error:'论文标识无效。'},400);const essay=await readEssay(id,user.userId);return essay?json({essay,essays:list.results,ready:connection.essayReady===true,online:connection.online}):json({error:'论文训练不存在。'},404);
 }catch{return json({error:'论文训练暂时无法读取，请重试。'},503);}
}
export async function POST(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  const raw=await request.text();if(raw.length>55000)return json({error:'项目材料或稿件过长。'},400);const b=JSON.parse(raw);if(!b||!validId(b.requestId))return json({error:'请求标识无效。'},400);
  const db=database();
  if(b.action==='create'){
   let input;try{input=essayInput(b);}catch(e){return json({error:e instanceof Error?e.message:'论文材料无效。'},400);}
   await db.prepare('INSERT OR IGNORE INTO textbook_essays(id,owner_id,title,topic,requirements,project_facts,drafts_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)').bind(b.requestId,user.userId,input.title,input.topic,input.requirements,input.projectFacts,JSON.stringify(input.drafts),now(),now()).run();
   const row=await db.prepare('SELECT * FROM textbook_essays WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();
   return row&&JSON.stringify(fields(row))===JSON.stringify(input)?json({essay:await readEssay(b.requestId,user.userId)},201):json({error:'请求标识已用于其他项目材料。'},409);
  }
  if(!validId(b.essayId)||!Number.isInteger(b.version)||b.version<0)return json({error:'论文版本或标识无效。'},400);
  const row=await db.prepare('SELECT * FROM textbook_essays WHERE id=? AND owner_id=?').bind(b.essayId,user.userId).first();if(!row)return json({error:'论文训练不存在。'},404);
  if(b.action==='save'){
   let input;try{input=essayInput(b);}catch(e){return json({error:e instanceof Error?e.message:'论文材料无效。'},400);}
   if(row.last_save_id===b.requestId)return JSON.stringify(fields(row))===JSON.stringify(input)?json({essay:await readEssay(b.essayId,user.userId)}):json({error:'请求标识已用于其他修改。'},409);
   if(row.version!==b.version)return json({error:'材料已在其他页面更新，请重新打开后再保存；当前草稿仍保留。'},409);
   const changed=await db.prepare('UPDATE textbook_essays SET title=?,topic=?,requirements=?,project_facts=?,drafts_json=?,version=version+1,last_save_id=?,updated_at=? WHERE id=? AND owner_id=? AND version=? RETURNING id').bind(input.title,input.topic,input.requirements,input.projectFacts,JSON.stringify(input.drafts),b.requestId,now(),b.essayId,user.userId,b.version).first();
   return changed?json({essay:await readEssay(b.essayId,user.userId)}):json({error:'材料已更新，请重新打开后保存。'},409);
  }
  if(b.action!=='run')return json({error:'训练动作无效。'},400);
  const previous=await db.prepare('SELECT * FROM textbook_essay_runs WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();
  if(previous)return previous.essay_id===b.essayId&&previous.essay_version===b.version&&previous.kind===b.kind&&previous.section===(b.kind==='feedback'?b.section:'')?json({essay:await readEssay(b.essayId,user.userId)},202):json({error:'请求标识已用于另一项训练。'},409);
  if(row.version!==b.version)return json({error:'请使用最新材料版本生成或点评。'},409);
  let task;try{task=essayTask(fields(row),Number(row.version),b.kind,b.section);}catch(e){return json({error:e instanceof Error?e.message:'训练参数无效。'},400);}
  if(!(await bridgeState()).essayReady)return json({error:'论文训练尚未连接，请保持 Langflow、Ollama 和教材连接器运行。稿件已保留。'},503);
  await expireJobs();const payload=JSON.stringify(task),query=(task.topic+' '+task.requirements).replace(/[\r\n<>]/g,' ').slice(0,1800);
  await db.batch([
   db.prepare('INSERT OR IGNORE INTO textbook_sessions(id,owner_id,title,created_at,updated_at) VALUES(?,?,?,?,?)').bind(b.essayId,user.userId,row.title,now(),now()),
   db.prepare(`INSERT OR IGNORE INTO textbook_jobs(id,session_id,owner_id,question,status,created_at,task_type,task_payload_json)
    SELECT ?,?,?,?,'queued',?,'essay',? WHERE (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running'))<3
    AND NOT EXISTS(SELECT 1 FROM textbook_jobs WHERE session_id=? AND status IN ('queued','running'))
    AND EXISTS(SELECT 1 FROM textbook_essays WHERE id=? AND owner_id=? AND version=?)`).bind(b.requestId,b.essayId,user.userId,query,now(),payload,b.essayId,b.essayId,user.userId,b.version),
   db.prepare('INSERT OR IGNORE INTO textbook_essay_runs(id,owner_id,essay_id,essay_version,kind,section,payload_json,created_at) SELECT ?,?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM textbook_jobs WHERE id=? AND owner_id=? AND task_payload_json=?)').bind(b.requestId,user.userId,b.essayId,b.version,b.kind,b.kind==='feedback'?b.section:'',payload,now(),b.requestId,user.userId,payload)]);
  const saved=await db.prepare('SELECT id FROM textbook_essay_runs WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();return saved?json({essay:await readEssay(b.essayId,user.userId)},202):json({error:'当前已有训练排队或材料已更新，请稍后重试。'},409);
 }catch(e){return json({error:e instanceof SyntaxError?'提交内容格式无效。':'论文训练提交失败，当前稿件已保留。'},e instanceof SyntaxError?400:503);}
}
