import { bridgeAuth, CLAIM_SQL, COMPLETE_SQL, database, expireJobs, json, now } from '../../../../lib/textbook/server';
import { cleanAnswer, validId } from '../../../../lib/textbook/policy';

export async function POST(request: Request) {
  if (!bridgeAuth(request)) return json({error:'Unauthorized'},401);
  try {
    if (Number(request.headers.get('content-length') ?? 0)>250000) return json({error:'Payload too large'},413);
    const body = await request.json() as Record<string,unknown>;
    if (body.action === 'heartbeat') {
      await database().prepare('INSERT INTO textbook_bridge (id,last_seen,ready) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, ready=excluded.ready').bind('desktop',now(),body.ready===true?1:0).run();
      return json({ok:true});
    }
    if (body.action === 'claim') {
      await expireJobs();
      const job = await database().prepare(CLAIM_SQL).bind(crypto.randomUUID(),now()).first();
      return json({job});
    }
    if (body.action === 'complete' && validId(body.id) && validId(body.lease)) {
      const answer = typeof body.answer === 'string' ? cleanAnswer(body.answer).slice(0,60000) : '';
      const error = typeof body.error === 'string' ? body.error.slice(0,300) : '';
      if (!answer && !error) return json({error:'Empty result'},400);
      const changed = await database().prepare(COMPLETE_SQL).bind(answer?'done':'failed',answer||null,error||null,now(),Math.max(0,Math.min(240000,Number(body.elapsedMs)||0)),body.id,body.lease,now()-240).first();
      return json({ok:Boolean(changed)},changed?200:409);
    }
    return json({error:'Invalid action'},400);
  } catch (error) {
    console.error('textbook bridge',error instanceof Error ? error.name : 'error');
    return json({error:'Bridge temporarily unavailable'},503);
  }
}
