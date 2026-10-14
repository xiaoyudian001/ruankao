import { env } from 'cloudflare:workers';
import { getChatGPTUser } from '../../app/chatgpt-auth';
import { bridgeAuthorized, bridgeOnline, availableRetrievalModes, isOwner } from './policy';

type Runtime = { DB?: D1Database; BUCKET?:R2Bucket; RAG_BRIDGE_SECRET?: string; RAG_OWNER_EMAIL?: string; RAG_SITE_ORIGIN?: string };
export const runtime = () => env as unknown as Runtime;
export const now = () => Math.floor(Date.now() / 1000);
export function database(): D1Database {
  const db = runtime().DB;
  if (!db) throw new Error('Database unavailable');
  return db;
}
export const json = (data: unknown, status = 200) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store' } });
export async function owner() {
  const user = await getChatGPTUser();
  return isOwner(user, runtime().RAG_OWNER_EMAIL ?? '') ? user : null;
}
export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get('origin');
  return Boolean(origin && origin === (runtime().RAG_SITE_ORIGIN ?? new URL(request.url).origin));
}
export const bridgeAuth = (request: Request) => bridgeAuthorized(request.headers.get('authorization'), runtime().RAG_BRIDGE_SECRET ?? '');
export async function bridgeState() {
  const state = await database().prepare('SELECT last_seen, ready, modes, conversation_ready, sources_ready,critique_ready,exam_ready,screenshot_ready,essay_ready FROM textbook_bridge WHERE id = ?').bind('desktop').first<{ last_seen: number; ready: number; modes:string;conversation_ready:number;sources_ready:number;critique_ready:number;exam_ready:number;screenshot_ready:number;essay_ready:number }>();
  return { online: bridgeOnline(state, now()), availableModes:availableRetrievalModes(state,now()),conversationReady:bridgeOnline(state,now())&&state?.conversation_ready===1,sourcesReady:bridgeOnline(state,now())&&state?.sources_ready===1,critiqueReady:Boolean(state&&now()-state.last_seen<35&&state.critique_ready===1),examReady:bridgeOnline(state,now())&&state?.exam_ready===1,screenshotReady:bridgeOnline(state,now())&&state?.screenshot_ready===1,essayReady:bridgeOnline(state,now())&&state?.essay_ready===1 };
}
export async function expireJobs() {
  await database().batch([
    database().prepare("UPDATE textbook_jobs SET status='failed', error=?, completed_at=? WHERE status='queued' AND created_at < ?").bind('电脑未及时领取问题，请检查连接后重试。', now(), now()-180),
    database().prepare("UPDATE textbook_jobs SET status=CASE WHEN cancel_requested=1 THEN 'cancelled' ELSE 'failed' END, answer=CASE WHEN cancel_requested=1 THEN partial_answer ELSE answer END,error=CASE WHEN cancel_requested=1 THEN NULL ELSE ? END,completed_at=?,lease=NULL WHERE status='running' AND leased_at < ?").bind('回答超时，请检查本地服务后重试。', now(), now()-240),
  ]);
}

export const CLAIM_SQL = `UPDATE textbook_jobs SET status='running', lease=?, leased_at=?
WHERE id = (SELECT id FROM textbook_jobs WHERE status='queued' ORDER BY created_at, rowid LIMIT 1)
AND status='queued' AND NOT EXISTS (SELECT 1 FROM textbook_jobs WHERE status='running')
AND NOT EXISTS (SELECT 1 FROM textbook_critiques WHERE status='running')
RETURNING id, question, session_id, lease, retrieval_mode, history_json, task_type, screenshot_json, task_payload_json`;

export const COMPLETE_SQL = `UPDATE textbook_jobs SET status=CASE WHEN cancel_requested=1 THEN 'cancelled' ELSE ? END, answer=CASE WHEN cancel_requested=1 THEN partial_answer ELSE ? END, error=CASE WHEN cancel_requested=1 THEN NULL ELSE ? END, completed_at=?, elapsed_ms=?, retrieval_query=?, rewrite_route=?, references_json=CASE WHEN cancel_requested=1 THEN '[]' ELSE ? END, exam_json=CASE WHEN cancel_requested=1 THEN NULL ELSE ? END, token_usage_json=CASE WHEN cancel_requested=1 THEN NULL ELSE ? END, lease=NULL
WHERE id=? AND status='running' AND lease=? AND leased_at >= ? RETURNING id`;

export const HISTORY_SQL = `SELECT question,answer FROM textbook_jobs
WHERE owner_id=? AND session_id=? AND status='done' AND answer IS NOT NULL AND task_type IN ('qa','exam')
ORDER BY created_at DESC,rowid DESC LIMIT 3`;
