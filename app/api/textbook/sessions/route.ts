import {database,expireJobs,json,now,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {DELETE_SESSION,LIVE_CHAT,sessionPage,sessionTitle,searchText} from '../../../../lib/textbook/sessions';
export async function GET(request:Request){
 try{const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
 const p=new URL(request.url).searchParams;return json(await sessionPage(user.userId,searchText(p.get('q')),p.get('cursor')));
 }catch(e){return json({error:e instanceof Error&&/搜索词|分页标识/.test(e.message)?e.message:'历史会话暂时无法读取，请重试。'},e instanceof Error&&/搜索词|分页标识/.test(e.message)?400:503);}
}
export async function PATCH(request:Request){
 try{const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
 const raw=await request.text();if(raw.length>1000)return json({error:'请求过长。'},400);const b=JSON.parse(raw);if(!validId(b.sessionId))return json({error:'会话标识无效。'},400);const title=sessionTitle(b.title);
 const changed=await database().prepare(`UPDATE textbook_sessions SET title=? WHERE id=? AND ${LIVE_CHAT} RETURNING id,title`).bind(title,b.sessionId,user.userId).first();
 return changed?json({session:changed}):json({error:'会话不存在或已删除。'},404);
 }catch(e){return json({error:e instanceof Error&&e.message.startsWith('会话名称')?e.message:'重命名失败，请重试。'},e instanceof SyntaxError||e instanceof Error&&e.message.startsWith('会话名称')?400:503);}
}
export async function DELETE(request:Request){
 try{const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
 const raw=await request.text();if(raw.length>300)return json({error:'请求过长。'},400);const b=JSON.parse(raw);if(!validId(b.sessionId))return json({error:'会话标识无效。'},400);
 await expireJobs();const db=database();
 await db.prepare(DELETE_SESSION).bind(now(),b.sessionId,user.userId).run();
 const removed=await db.prepare('SELECT session_id FROM textbook_session_deletions WHERE session_id=? AND owner_id=?').bind(b.sessionId,user.userId).first();if(removed)return json({deleted:true,sessionId:b.sessionId});
 const existing=await db.prepare(`SELECT id FROM textbook_sessions WHERE id=? AND ${LIVE_CHAT} AND NOT EXISTS (SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND j.task_type NOT IN ('qa','exam'))`).bind(b.sessionId,user.userId).first();
 return existing?json({error:'此会话仍有任务正在处理，完成后再删除。'},409):json({error:'会话不存在。'},404);
 }catch(e){return json({error:'删除未确认，请重试；原会话暂时保留。'},e instanceof SyntaxError?400:503);}
}
