import { bridgeState, database, expireJobs, json, now, owner, sameOrigin, HISTORY_SQL } from '../../../../lib/textbook/server';
import { validId, validQuestion, validRetrievalMode, sameJobRequest } from '../../../../lib/textbook/policy';
import { historySnapshot } from '../../../../lib/textbook/conversation';
import { sourceSummaries } from '../../../../lib/textbook/sources';
import {validTaskType,sameTaskRequest,savedPractice,practiceView} from '../../../../lib/textbook/exam';
import {parseManifest} from '../../../../lib/textbook/screenshots';
import {LIVE_CHAT,UNDELETED_SESSION} from '../../../../lib/textbook/sessions';

export async function GET(request: Request) {
  try {
    const user = await owner();
    if (!user) return json({error:'请使用网站所有者的 ChatGPT 账号登录。'},403);
    await expireJobs();
    const params = new URL(request.url).searchParams;
    const requestedSession = params.get('sessionId');
    const requestId = params.get('requestId');
    const recovered = requestId && validId(requestId) ? await database().prepare("SELECT session_id FROM textbook_jobs WHERE id=? AND owner_id=? AND task_type IN ('qa','exam') AND NOT EXISTS(SELECT 1 FROM textbook_session_deletions d WHERE d.session_id=textbook_jobs.session_id)").bind(requestId,user.userId).first<{session_id:string}>() : null;
    const candidate = recovered?.session_id ?? (requestedSession && validId(requestedSession) ? requestedSession : null);
    const visible=candidate?await database().prepare(UNDELETED_SESSION).bind(candidate,user.userId).first():null;
    const sessionId=visible?candidate:null;
    const sessions = await database().prepare(`SELECT id, title, updated_at FROM textbook_sessions WHERE ${LIVE_CHAT} ORDER BY updated_at DESC,id DESC LIMIT 50`).bind(user.userId).all();
    const messages = sessionId ? await database().prepare("SELECT id, question, status, answer, error, elapsed_ms, created_at, leased_at, retrieval_mode, retrieval_query, rewrite_route, references_json, task_type, exam_json, practice_choice,screenshot_json FROM textbook_jobs WHERE owner_id=? AND session_id=? AND task_type IN ('qa','exam') ORDER BY created_at,rowid LIMIT 200").bind(user.userId,sessionId).all() : {results:[]};
    const summaries=messages.results.map(row=>{const {references_json,exam_json,practice_choice,screenshot_json,...message}=row;const refs=sourceSummaries(references_json);let practice=null,screenshotId=null,screenshotCount=0;try{practice=practiceView(savedPractice(exam_json,refs.map(r=>r.rank)),practice_choice);}catch{/* Preserve a usable original answer if practice is corrupt. */}try{if(screenshot_json){const manifest=parseManifest(screenshot_json);screenshotId=manifest.recognitionId;screenshotCount=manifest.images.length;}}catch{}return {...message,references:refs,practice,screenshotId,screenshotCount};});
    return json({sessions:sessions.results,messages:summaries,selectedSessionId:sessionId,serverNow:now(),...await bridgeState()});
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
    const mode=validRetrievalMode(body.retrievalMode);
    const taskType=validTaskType(body.taskType);
    if(body.screenshotId!=null&&(!validId(body.screenshotId)||taskType!=='exam'))return json({error:'截图只用于真题解析。'},400);
    if (!validId(body.requestId) || (body.sessionId != null && !validId(body.sessionId))) return json({error:'会话标识无效。'},400);
    const existing = await database().prepare('SELECT id,session_id,status,question,retrieval_mode,task_type,screenshot_json FROM textbook_jobs WHERE id=? AND owner_id=?').bind(body.requestId,user.userId).first<{id:string;session_id:string;status:string;question:string;retrieval_mode:string;task_type:string;screenshot_json:string|null}>();
    const targetSession=existing?.session_id??body.sessionId;
    if(targetSession&&await database().prepare('SELECT session_id FROM textbook_session_deletions WHERE session_id=? AND owner_id=?').bind(targetSession,user.userId).first())return json({error:'此会话已删除，请新建会话。'},410);
    if (existing) {
      if (!sameJobRequest(existing,question,mode,body.sessionId)||!sameTaskRequest(existing.task_type,taskType)||(existing.screenshot_json?parseManifest(existing.screenshot_json).recognitionId:null)!==(body.screenshotId??null)) return json({error:'请求标识已用于其他问题、检索模式、题目类型或截图，请重新提交。'},409);
      return json({job:{id:existing.id,session_id:existing.session_id,status:existing.status,retrieval_mode:existing.retrieval_mode}});
    }
    await expireJobs();
    const connection=await bridgeState();
    if (!connection.online) return json({error:'电脑未连接。请启动教材问答连接，并保持 Langflow 和 Ollama 运行。'},503);
    if (!connection.availableModes.includes(mode)) return json({error:'所选检索模式暂不可用，请刷新连接或使用当前问答。'},503);
    if(taskType==='exam'&&!connection.examReady)return json({error:'真题解析暂不可用，请刷新连接后重试。'},503);
    let screenshotJson=null;
    if(body.screenshotId){
      if(!connection.screenshotReady)return json({error:'图文真题解析尚未连接，请刷新后重试。'},503);
      const recognized=await database().prepare("SELECT screenshot_json FROM textbook_jobs WHERE id=? AND owner_id=? AND task_type='recognize' AND status='done' AND recognition_json IS NOT NULL").bind(body.screenshotId,user.userId).first<{screenshot_json:string}>();
      if(!recognized)return json({error:'请先完成截图识别并核对题目。'},400);
      screenshotJson=JSON.stringify(parseManifest(recognized.screenshot_json));
    }
    const sessionId = body.sessionId ?? crypto.randomUUID();
    if (body.sessionId && !await database().prepare(UNDELETED_SESSION).bind(sessionId,user.userId).first()) return json({error:'会话不存在或已删除。'},404);
    const count = await database().prepare('SELECT COUNT(*) AS count FROM textbook_jobs WHERE session_id=?').bind(sessionId).first<{count:number}>();
    if ((count?.count ?? 0)>=200) return json({error:'此会话已达到 200 条，请新建会话。'},409);
    const history = taskType==='qa'&&connection.conversationReady && body.sessionId ? await database().prepare(HISTORY_SQL).bind(user.userId,sessionId).all<{question:string;answer:string}>() : {results:[]};
    const snapshot=historySnapshot(history.results);
    // A single conditional INSERT is atomic, including pending limits and same-session exclusion.
    const result = await database().batch([
      database().prepare('INSERT OR IGNORE INTO textbook_sessions (id,owner_id,title,created_at,updated_at) VALUES (?,?,?,?,?)').bind(sessionId,user.userId,question.slice(0,32),now(),now()),
      database().prepare(`INSERT OR IGNORE INTO textbook_jobs (id,session_id,owner_id,question,status,created_at,retrieval_mode,history_json,task_type,screenshot_json)
        SELECT ?,?,?,?,'queued',?,?,?,?,? WHERE (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running')) < 3
        AND NOT EXISTS (SELECT 1 FROM textbook_jobs WHERE session_id=? AND status IN ('queued','running'))
        AND NOT EXISTS (SELECT 1 FROM textbook_session_deletions WHERE session_id=?)`).bind(body.requestId,sessionId,user.userId,question,now(),mode,snapshot,taskType,screenshotJson,sessionId,sessionId),
      database().prepare('UPDATE textbook_sessions SET updated_at=? WHERE id=? AND owner_id=?').bind(now(),sessionId,user.userId),
    ]);
    if (!result[1].meta.changes) return json({error:'已有问题正在处理，请等待完成后再发送。'},409);
    return json({job:{id:body.requestId,session_id:sessionId,status:'queued',retrieval_mode:mode}},202);
  } catch (error) {
    if (error instanceof Error && (error.message.startsWith('请输入') || error.message==='检索模式无效。'||error.message==='题目类型无效。')) return json({error:error.message},400);
    console.error('textbook submit',error instanceof Error ? error.name : 'error');
    return json({error:'发送失败，问题已保留，请重试。'},503);
  }
}
