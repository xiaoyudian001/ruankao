import { bridgeAuth, CLAIM_SQL, COMPLETE_SQL, database, expireJobs, json, now } from '../../../../lib/textbook/server';
import { cleanAnswer, validId, RETRIEVAL_MODES } from '../../../../lib/textbook/policy';
import { rewriteDiagnostic } from '../../../../lib/textbook/conversation';
import {references,PAGE_CLAIM_SQL} from '../../../../lib/textbook/sources';

export async function POST(request: Request) {
  if (!bridgeAuth(request)) return json({error:'Unauthorized'},401);
  try {
    if (Number(request.headers.get('content-length') ?? 0)>250000) return json({error:'Payload too large'},413);
    const body = await request.json() as Record<string,unknown>;
    if (body.action === 'heartbeat') {
      const modes=Array.isArray(body.modes)?Object.keys(RETRIEVAL_MODES).filter(mode=>(body.modes as unknown[]).includes(mode)):['default'];
      await database().prepare('INSERT INTO textbook_bridge (id,last_seen,ready,modes,conversation_ready,sources_ready) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, ready=excluded.ready, modes=excluded.modes, conversation_ready=excluded.conversation_ready, sources_ready=excluded.sources_ready').bind('desktop',now(),body.ready===true?1:0,JSON.stringify(modes),body.conversationReady===true?1:0,body.sourcesReady===true?1:0).run();
      return json({ok:true});
    }
    if (body.action === 'claim') {
      await expireJobs();
      const job = await database().prepare(CLAIM_SQL).bind(crypto.randomUUID(),now()).first();
      return json({job});
    }
    if (body.action==='pageClaim') {
      await database().prepare("UPDATE textbook_pages SET status='failed',error=?,lease=NULL,updated_at=? WHERE status IN ('queued','running') AND updated_at<?").bind('页面准备超时，请重试。',now(),now()-90).run();
      const page=await database().prepare(PAGE_CLAIM_SQL).bind(crypto.randomUUID(),now()).first();
      return json({page});
    }
    if (body.action==='pageFail'&&Number.isInteger(body.page)&&validId(body.lease)) {
      await database().prepare("UPDATE textbook_pages SET status='failed',error=?,lease=NULL,updated_at=? WHERE page=? AND status='running' AND lease=?").bind('原页暂时无法读取，请检查本地 PDF 后重试。',now(),body.page,body.lease).run();
      return json({ok:true});
    }
    if (body.action === 'complete' && validId(body.id) && validId(body.lease)) {
      const answer = typeof body.answer === 'string' ? cleanAnswer(body.answer).slice(0,60000) : '';
      const error = typeof body.error === 'string' ? body.error.slice(0,300) : '';
      if (!answer && !error) return json({error:'Empty result'},400);
      const diagnostic=rewriteDiagnostic(body);
      const refs=references(body.references);
      const changed = await database().prepare(COMPLETE_SQL).bind(answer?'done':'failed',answer||null,error||null,now(),Math.max(0,Math.min(240000,Number(body.elapsedMs)||0)),diagnostic.query,diagnostic.route,JSON.stringify(refs),body.id,body.lease,now()-240).first();
      return json({ok:Boolean(changed)},changed?200:409);
    }
    return json({error:'Invalid action'},400);
  } catch (error) {
    console.error('textbook bridge',error instanceof Error ? error.name : 'error');
    return json({error:'Bridge temporarily unavailable'},503);
  }
}
