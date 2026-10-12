import {bridgeState,database,expireJobs,json,now,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {sourceSummaries,storedReferences} from '../../../../lib/textbook/sources';
import {caseInput,casePrompt,type StudyCase,type CaseQuestion} from '../../../../lib/cases/model';
import {critiqueSummary,expireCritiques} from '../../../../lib/review/critique-server';

async function readCase(id:string,userId:string):Promise<StudyCase|null>{
 const db=database(),c=await db.prepare('SELECT * FROM textbook_cases WHERE id=? AND owner_id=?').bind(id,userId).first();
 if(!c)return null;
 const rows=await db.prepare('SELECT q.*,j.status AS analysis_status,j.answer,j.error AS analysis_error,j.references_json FROM textbook_case_questions q LEFT JOIN textbook_jobs j ON j.id=q.job_id AND j.owner_id=q.owner_id WHERE q.case_id=? AND q.owner_id=? ORDER BY q.ordinal').bind(id,userId).all();
 const questions:CaseQuestion[]=[];
 for(const q of rows.results){
  const attempts=await db.prepare('SELECT a.id,a.response,a.created_at,c.status,c.result_json,c.error,c.references_json FROM textbook_case_attempts a LEFT JOIN textbook_critiques c ON c.id=a.id AND c.owner_id=a.owner_id WHERE a.question_id=? AND a.owner_id=? ORDER BY a.created_at,a.rowid').bind(q.id,userId).all();
  questions.push({id:String(q.id),prompt:String(q.prompt),jobId:String(q.job_id),ordinal:Number(q.ordinal),
   // Never send a reference answer before the user has saved an answer to this question.
   analysis:attempts.results.length&&q.analysis_status==='done'?{answer:String(q.answer),references:sourceSummaries(q.references_json)}:null,
   attempts:attempts.results.map(a=>({id:String(a.id),response:String(a.response),createdAt:Number(a.created_at),status:a.status?String(a.status):q.analysis_status==='failed'?'analysis_failed':q.analysis_status==='done'?(storedReferences(q.references_json).length?'awaiting_critique':'no_evidence'):'awaiting_analysis',error:a.error?String(a.error):q.analysis_status==='failed'?String(q.analysis_error??'参考分析失败，请重新提交。'):null,critique:a.status?critiqueSummary(a):null}))});
 }
 return {id:String(c.id),title:String(c.title),background:String(c.background),createdAt:Number(c.created_at),questions};
}

export async function GET(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  await expireJobs();await expireCritiques();
  const id=new URL(request.url).searchParams.get('id'),db=database();
  const rows=await db.prepare('SELECT c.id,c.title,c.created_at AS createdAt,COUNT(q.id) AS questionCount FROM textbook_cases c LEFT JOIN textbook_case_questions q ON q.case_id=c.id AND q.owner_id=c.owner_id WHERE c.owner_id=? GROUP BY c.id ORDER BY c.created_at DESC,c.rowid DESC LIMIT 50').bind(user.userId).all();
  const connection=await bridgeState();
  if(!id)return json({cases:rows.results,online:connection.online,ready:connection.examReady&&connection.critiqueReady});
  if(!validId(id))return json({error:'案例标识无效。'},400);
  const c=await readCase(id,user.userId);return c?json({case:c,cases:rows.results,online:connection.online,ready:connection.examReady&&connection.critiqueReady}):json({error:'案例不存在。'},404);
 }catch{return json({error:'案例暂时无法读取，请重试。'},503);}
}

export async function POST(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  const raw=await request.text();if(raw.length>22000)return json({error:'案例或答案内容过长。'},400);
  const b=JSON.parse(raw),db=database();
  if(!validId(b.requestId))return json({error:'请求标识无效。'},400);
  if(b.action==='create'){
   let input;try{input=caseInput(b);}catch(e){return json({error:e instanceof Error?e.message:'案例格式无效。'},400);}
   const previous=await readCase(b.requestId,user.userId);
   if(previous){return previous.title===input.title&&previous.background===input.background&&JSON.stringify(previous.questions.map(q=>q.prompt))===JSON.stringify(input.questions)?json({case:previous},201):json({error:'请求标识已用于另一个案例。'},409);}
   await db.batch([
    db.prepare('INSERT OR IGNORE INTO textbook_cases(id,owner_id,title,background,created_at) VALUES(?,?,?,?,?)').bind(b.requestId,user.userId,input.title,input.background,now()),
    ...input.questions.map((q,i)=>db.prepare('INSERT OR IGNORE INTO textbook_case_questions(id,case_id,owner_id,prompt,ordinal,job_id,created_at) SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM textbook_cases WHERE id=? AND owner_id=? AND title=? AND background=?)').bind(crypto.randomUUID(),b.requestId,user.userId,q,i+1,crypto.randomUUID(),now(),b.requestId,user.userId,input.title,input.background))]);
   const c=await readCase(b.requestId,user.userId);
   return c&&c.title===input.title&&c.background===input.background&&JSON.stringify(c.questions.map(q=>q.prompt))===JSON.stringify(input.questions)?json({case:c},201):json({error:'案例标识冲突，请刷新后重试。'},409);
  }
  if(!['submit','advance'].includes(b.action)||!validId(b.caseId)||!validId(b.questionId))return json({error:'案例请求无效。'},400);
  const q=await db.prepare('SELECT q.*,c.background,c.title FROM textbook_case_questions q JOIN textbook_cases c ON c.id=q.case_id AND c.owner_id=q.owner_id WHERE q.id=? AND q.case_id=? AND q.owner_id=?').bind(b.questionId,b.caseId,user.userId).first();
  if(!q)return json({error:'案例小问不存在。'},404);
  await expireJobs();await expireCritiques();
  if(b.action==='submit'){
   if(typeof b.response!=='string'||!b.response.trim()||b.response.length>5000)return json({error:'请先写下自己的答案，最多5000字。'},400);
   const response=b.response.trim();
   const old=await db.prepare('SELECT * FROM textbook_case_attempts WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();
   if(old)return old.question_id===q.id&&old.response===response?json({case:await readCase(b.caseId,user.userId)},202):json({error:'请求标识已用于其他作答。'},409);
   const connection=await bridgeState();if(!connection.examReady||!connection.critiqueReady)return json({error:'请保持本机教材检索和点评流程连接；草稿仍保留在此浏览器。'},503);
   await db.batch([
    db.prepare('INSERT OR IGNORE INTO textbook_sessions(id,owner_id,title,created_at,updated_at) VALUES(?,?,?,?,?)').bind(b.caseId,user.userId,q.title,now(),now()),
    db.prepare("INSERT OR IGNORE INTO textbook_jobs(id,session_id,owner_id,question,status,created_at,task_type) SELECT ?,?,?,?,'queued',?,'case' WHERE (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running'))<3").bind(q.job_id,b.caseId,user.userId,casePrompt(String(q.background),String(q.prompt)),now()),
    db.prepare("UPDATE textbook_jobs SET status='queued',error=NULL,answer=NULL,lease=NULL,created_at=? WHERE id=? AND owner_id=? AND status='failed' AND (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running'))<3").bind(now(),q.job_id,user.userId),
    db.prepare("INSERT OR IGNORE INTO textbook_case_attempts(id,question_id,owner_id,response,created_at) SELECT ?,?,?,?,? WHERE EXISTS(SELECT 1 FROM textbook_jobs WHERE id=? AND owner_id=? AND status IN ('queued','running','done'))").bind(b.requestId,q.id,user.userId,response,now(),q.job_id,user.userId)]);
   const saved=await db.prepare('SELECT response,question_id FROM textbook_case_attempts WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();
   if(!saved)return json({error:'分析队列繁忙，请稍后提交；草稿已保留。'},409);
   if(saved.question_id!==q.id||saved.response!==response)return json({error:'请求标识已用于其他作答。'},409);
  }
  const a=await db.prepare('SELECT * FROM textbook_case_attempts WHERE id=? AND question_id=? AND owner_id=?').bind(b.requestId,q.id,user.userId).first();
  if(!a)return json({error:'请先提交当前小问的答案。'},404);
  const job=await db.prepare("SELECT answer,references_json FROM textbook_jobs WHERE id=? AND owner_id=? AND status='done'").bind(q.job_id,user.userId).first();
  if(job&&storedReferences(job.references_json).length&&(await bridgeState()).critiqueReady){
   await db.prepare(`INSERT OR IGNORE INTO textbook_critiques(id,owner_id,card_id,card_version,job_id,front,back,response,references_json,status,created_at)
    SELECT ?,?,?,0,?,?,?,?,?,'queued',? WHERE (SELECT COUNT(*) FROM textbook_critiques WHERE status IN ('queued','running'))<3`).bind(a.id,user.userId,q.id,q.job_id,casePrompt(String(q.background),String(q.prompt)),job.answer,a.response,job.references_json,now()).run();
  }
  return json({case:await readCase(b.caseId,user.userId)},202);
 }catch(e){return json({error:e instanceof SyntaxError?'提交内容格式无效。':'案例提交失败，草稿已保留。'},e instanceof SyntaxError?400:503);}
}
