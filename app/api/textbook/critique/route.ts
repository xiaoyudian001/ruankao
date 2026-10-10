import {bridgeState,database,json,now,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {storedReferences} from '../../../../lib/textbook/sources';
import {critiqueSummary,expireCritiques} from '../../../../lib/review/critique-server';

export async function GET(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  const id=new URL(request.url).searchParams.get('id');if(!validId(id))return json({error:'点评标识无效。'},400);
  await expireCritiques();const job=await database().prepare('SELECT * FROM textbook_critiques WHERE id=? AND owner_id=?').bind(id,user.userId).first();
  return job?json({critique:critiqueSummary(job)}):json({error:'点评不存在。'},404);
 }catch{return json({error:'点评暂时无法读取，请重试。'},503);}
}
export async function POST(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  const raw=await request.text();if(raw.length>12000)return json({error:'回忆内容过长。'},400);
  const b=JSON.parse(raw) as Record<string,unknown>;
  if(!validId(b.requestId)||!validId(b.cardId)||!Number.isInteger(b.version)||Number(b.version)<0||typeof b.response!=='string'||b.response.length>5000)return json({error:'卡片版本或回忆内容无效。'},400);
  const db=database();await expireCritiques();
  const previous=await db.prepare('SELECT * FROM textbook_critiques WHERE id=? AND owner_id=?').bind(b.requestId,user.userId).first();
  if(previous)return previous.card_id===b.cardId&&previous.card_version===b.version&&previous.response===b.response?json({critique:critiqueSummary(previous)}):json({error:'请求标识已用于其他点评。'},409);
  const card=await db.prepare('SELECT c.*,f.references_json,f.job_id FROM textbook_cards c JOIN textbook_favorites f ON f.id=c.favorite_id AND f.owner_id=c.owner_id WHERE c.id=? AND c.owner_id=?').bind(b.cardId,user.userId).first();
  if(!card)return json({error:'卡片不存在。'},404);
  if(card.version!==b.version)return json({error:'卡片已更新，请刷新后再点评。'},409);
  const refs=storedReferences(card.references_json);if(!refs.length)return json({error:'这张卡片没有保存教材片段，暂时无法提供有依据的 AI 点评。请继续自评。'},422);
  const connection=await bridgeState();if(!connection.critiqueReady)return json({error:'AI 点评需要电脑连接和 MiniMax 点评流程。你仍可继续自评。'},503);
  // Identical in-flight requests from separate tabs share one model execution.
  await db.prepare(`INSERT OR IGNORE INTO textbook_critiques(id,owner_id,card_id,card_version,job_id,front,back,response,references_json,status,created_at)
    SELECT ?,?,?,?,?,?,?,?,?,'queued',? WHERE (SELECT COUNT(*) FROM textbook_critiques WHERE status IN ('queued','running'))<3
    AND NOT EXISTS(SELECT 1 FROM textbook_critiques WHERE owner_id=? AND card_id=? AND card_version=? AND response=? AND status IN ('queued','running'))
    AND EXISTS(SELECT 1 FROM textbook_cards WHERE id=? AND owner_id=? AND version=?)`).bind(b.requestId,user.userId,b.cardId,b.version,card.job_id,card.front,card.back,b.response,JSON.stringify(refs),now(),user.userId,b.cardId,b.version,b.response,b.cardId,user.userId,b.version).run();
  const job=await db.prepare("SELECT * FROM textbook_critiques WHERE owner_id=? AND card_id=? AND card_version=? AND response=? AND (id=? OR status IN ('queued','running')) ORDER BY created_at DESC LIMIT 1").bind(user.userId,b.cardId,b.version,b.response,b.requestId).first();
  return job?json({critique:critiqueSummary(job)},202):json({error:'点评正在排队或卡片已更新，请稍后重试。'},409);
 }catch(error){return json({error:error instanceof SyntaxError?'提交内容格式无效。':'点评提交失败，回忆内容已保留。'},error instanceof SyntaxError?400:503);}
}
