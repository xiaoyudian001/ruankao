import {database,json,owner} from '../../../../lib/textbook/server';
import {LIVE_CHAT} from '../../../../lib/textbook/sessions';
import {validId} from '../../../../lib/textbook/policy';
import {exportMarkdown,type ExportJob} from '../../../../lib/textbook/export';
export async function GET(request:Request){
 try{const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  const id=new URL(request.url).searchParams.get('sessionId');if(!validId(id))return json({error:'会话标识无效。'},400);
  const db=database(),session=await db.prepare(`SELECT title FROM textbook_sessions WHERE id=? AND ${LIVE_CHAT}`).bind(id,user.userId).first<{title:string}>();if(!session)return json({error:'会话不存在或已删除。'},404);
  const rows=await db.prepare("SELECT id,question,status,answer,error,created_at,retrieval_mode,task_type,answer_action,source_job_id,references_json,screenshot_json FROM textbook_jobs WHERE session_id=? AND owner_id=? AND task_type IN ('qa','exam') ORDER BY created_at,rowid LIMIT 200").bind(id,user.userId).all<ExportJob>();
  return new Response(exportMarkdown(session.title,rows.results,new URL(request.url).origin),{headers:{'Content-Type':'text/markdown; charset=utf-8','Content-Disposition':`attachment; filename="conversation-${id.slice(0,8)}.md"`,'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
 }catch{return json({error:'会话导出失败，请稍后重试。'},503);}
}
