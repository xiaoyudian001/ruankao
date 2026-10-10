import { bridgeAuth, CLAIM_SQL, COMPLETE_SQL, database, expireJobs, json, now } from '../../../../lib/textbook/server';
import { cleanAnswer, validId, RETRIEVAL_MODES } from '../../../../lib/textbook/policy';
import { rewriteDiagnostic } from '../../../../lib/textbook/conversation';
import {references,PAGE_CLAIM_SQL} from '../../../../lib/textbook/sources';
import {storedReferences} from '../../../../lib/textbook/sources';
import {CRITIQUE_CLAIM_SQL,CRITIQUE_COMPLETE_SQL,expireCritiques} from '../../../../lib/review/critique-server';
import {validateCritique} from '../../../../lib/review/critique';

export async function POST(request: Request) {
  if (!bridgeAuth(request)) return json({error:'Unauthorized'},401);
  try {
    if (Number(request.headers.get('content-length') ?? 0)>250000) return json({error:'Payload too large'},413);
    const body = await request.json() as Record<string,unknown>;
    if (body.action === 'heartbeat') {
      const modes=Array.isArray(body.modes)?Object.keys(RETRIEVAL_MODES).filter(mode=>(body.modes as unknown[]).includes(mode)):['default'];
      await database().prepare('INSERT INTO textbook_bridge (id,last_seen,ready,modes,conversation_ready,sources_ready,critique_ready) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, ready=excluded.ready, modes=excluded.modes, conversation_ready=excluded.conversation_ready, sources_ready=excluded.sources_ready,critique_ready=excluded.critique_ready').bind('desktop',now(),body.ready===true?1:0,JSON.stringify(modes),body.conversationReady===true?1:0,body.sourcesReady===true?1:0,body.critiqueReady===true?1:0).run();
      return json({ok:true});
    }
    if (body.action === 'claim') {
      await expireJobs();
      await expireCritiques();
      const job = await database().prepare(CLAIM_SQL).bind(crypto.randomUUID(),now()).first();
      return json({job});
    }
    if(body.action==='critiqueClaim'){
      await expireJobs();await expireCritiques();
      const critique=await database().prepare(CRITIQUE_CLAIM_SQL).bind(crypto.randomUUID(),now()).first();return json({critique});
    }
    if(body.action==='critiqueComplete'&&validId(body.id)&&validId(body.lease)){
      const db=database();const job=await db.prepare("SELECT references_json FROM textbook_critiques WHERE id=? AND status='running' AND lease=? AND leased_at>=?").bind(body.id,body.lease,now()-180).first();
      if(!job)return json({error:'Late result'},409);
      let result=null,error=null;
      if(body.result!=null){try{result=validateCritique(body.result,storedReferences(job.references_json).map(r=>r.rank));}catch{return json({error:'Invalid critique result'},400);}}
      else error='AI 点评执行失败或超时，请稍后重试。你仍可继续自评。';
      const changed=await db.prepare(CRITIQUE_COMPLETE_SQL).bind(result?'done':'failed',result?JSON.stringify(result):null,error,now(),body.id,body.lease,now()-180).first();return json({ok:Boolean(changed)},changed?200:409);
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
