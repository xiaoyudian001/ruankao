import { bridgeState, database, expireJobs, json, now, owner, sameOrigin } from '../../../../lib/textbook/server';
import { validId, validQuestion } from '../../../../lib/textbook/policy';

export async function GET(request: Request) {
  try {
    const user = await owner();
    if (!user) return json({error:'请使用网站所有者的 ChatGPT 账号登录。'},403);
    await expireJobs();
    const sessionId = new URL(request.url).searchParams.get('sessionId');
    const sessions = await database().prepare('SELECT id, title, updated_at FROM textbook_sessions WHERE owner_id=? ORDER BY updated_at DESC LIMIT 50').bind(user.userId).all();
    const messages = sessionId && validId(sessionId) ? await database().prepare('SELECT id, question, status, answer, error, elapsed_ms, created_at FROM textbook_jobs WHERE owner_id=? AND session_id=? ORDER BY created_at,rowid LIMIT 200').bind(user.userId,sessionId).all() : {results:[]};
    return json({sessions:sessions.results,messages:messages.results,...await bridgeState()});
  } catch (error) {
    console.error('textbook read', error instanceof Error ? error.name : 'error');
    return json({error:'会话暂时无法读取，请稍后重试。'},503);
  }
}

export async function POST(request: Request) {
  try {
    const user = await owner();
    if (!user) return json({error:'请使用网站所有者的 ChatGPT 账号登录。'},403);
    if (!sameOrigin(request)) return json({error:'请求来源无效。'},403);
    if (Number(request.headers.get('content-length') ?? 0)>16000) return json({error:'问题过长。'},400);
    const body = await request.json() as Record<string,unknown>;
    const question = validQuestion(body.question);
    if (!validId(body.requestId) || (body.sessionId != null && !validId(body.sessionId))) return json({error:'会话标识无效。'},400);
    const existing = await database().prepare('SELECT id,session_id,status FROM textbook_jobs WHERE id=? AND owner_id=?').bind(body.requestId,user.userId).first();
    if (existing) return json({job:existing});
    await expireJobs();
    if (!(await bridgeState()).online) return json({error:'电脑未连接。请启动教材问答连接，并保持 Langflow 和 Ollama 运行。'},503);
    const sessionId = body.sessionId ?? crypto.randomUUID();
    if (body.sessionId && !await database().prepare('SELECT id FROM textbook_sessions WHERE id=? AND owner_id=?').bind(sessionId,user.userId).first()) return json({error:'会话不存在。'},404);
    const count = await database().prepare('SELECT COUNT(*) AS count FROM textbook_jobs WHERE session_id=?').bind(sessionId).first<{count:number}>();
    if ((count?.count ?? 0)>=200) return json({error:'此会话已达到 200 条，请新建会话。'},409);
    // A single conditional INSERT is atomic, including pending limits and same-session exclusion.
    const result = await database().batch([
      database().prepare('INSERT OR IGNORE INTO textbook_sessions (id,owner_id,title,created_at,updated_at) VALUES (?,?,?,?,?)').bind(sessionId,user.userId,question.slice(0,32),now(),now()),
      database().prepare(`INSERT OR IGNORE INTO textbook_jobs (id,session_id,owner_id,question,status,created_at)
        SELECT ?,?,?,?,'queued',? WHERE (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running')) < 3
        AND NOT EXISTS (SELECT 1 FROM textbook_jobs WHERE session_id=? AND status IN ('queued','running'))`).bind(body.requestId,sessionId,user.userId,question,now(),sessionId),
      database().prepare('UPDATE textbook_sessions SET updated_at=? WHERE id=? AND owner_id=?').bind(now(),sessionId,user.userId),
    ]);
    if (!result[1].meta.changes) return json({error:'已有问题正在处理，请等待完成后再发送。'},409);
    return json({job:{id:body.requestId,session_id:sessionId,status:'queued'}},202);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('请输入')) return json({error:error.message},400);
    console.error('textbook submit',error instanceof Error ? error.name : 'error');
    return json({error:'发送失败，问题已保留，请重试。'},503);
  }
}
