import { bridgeAuth, CLAIM_SQL, COMPLETE_SQL, database, expireJobs, json, now,runtime } from '../../../../lib/textbook/server';
import { cleanAnswer, validId, RETRIEVAL_MODES } from '../../../../lib/textbook/policy';
import { rewriteDiagnostic } from '../../../../lib/textbook/conversation';
import {references,PAGE_CLAIM_SQL} from '../../../../lib/textbook/sources';
import {storedReferences} from '../../../../lib/textbook/sources';
import {CRITIQUE_CLAIM_SQL,CRITIQUE_COMPLETE_SQL,expireCritiques} from '../../../../lib/review/critique-server';
import {validateCritique} from '../../../../lib/review/critique';
import {validatePractice} from '../../../../lib/textbook/exam';
import {parseManifest,validateRecognition,pngInfo} from '../../../../lib/textbook/screenshots';
import {progressSnapshot,PROGRESS_SQL,STOPPED_SQL} from '../../../../lib/textbook/streaming';

export async function POST(request: Request) {
  if (!bridgeAuth(request)) return json({error:'Unauthorized'},401);
  try {
    if (Number(request.headers.get('content-length') ?? 0)>250000) return json({error:'Payload too large'},413);
    const body = await request.json() as Record<string,unknown>;
    if(['control','progress','stopped'].includes(String(body.action))){
      if(!validId(body.id)||!validId(body.lease))return json({error:'Invalid job control'},400);
      const db=database(),job=await db.prepare("SELECT cancel_requested,partial_seq FROM textbook_jobs WHERE id=? AND lease=? AND status='running' AND leased_at>=? AND task_type IN ('qa','exam')").bind(body.id,body.lease,now()-240).first<{cancel_requested:number;partial_seq:number}>();
      if(!job)return json({error:'Late job control'},409);
      if(body.action==='control')return json({ok:true,cancelRequested:job.cancel_requested===1});
      if(body.action==='stopped'){const changed=await db.prepare(STOPPED_SQL).bind(now(),body.id,body.lease,now()-240).first();return json({ok:Boolean(changed)},changed?200:409);}
      let snapshot;try{snapshot=progressSnapshot(body);}catch{return json({error:'Invalid progress'},400);}
      await db.prepare(PROGRESS_SQL).bind(snapshot.text,snapshot.seq,body.id,body.lease,now()-240,snapshot.seq).first();
      const current=await db.prepare("SELECT cancel_requested FROM textbook_jobs WHERE id=? AND lease=? AND status='running' AND leased_at>=?").bind(body.id,body.lease,now()-240).first<{cancel_requested:number}>();
      return current?json({ok:true,cancelRequested:current.cancel_requested===1}):json({error:'Late progress'},409);
    }
    if (body.action === 'heartbeat') {
      const modes=Array.isArray(body.modes)?Object.keys(RETRIEVAL_MODES).filter(mode=>(body.modes as unknown[]).includes(mode)):['default'];
      await database().prepare('INSERT INTO textbook_bridge (id,last_seen,ready,modes,conversation_ready,sources_ready,critique_ready,exam_ready,screenshot_ready,essay_ready) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, ready=excluded.ready, modes=excluded.modes, conversation_ready=excluded.conversation_ready, sources_ready=excluded.sources_ready,critique_ready=excluded.critique_ready,exam_ready=excluded.exam_ready,screenshot_ready=excluded.screenshot_ready,essay_ready=excluded.essay_ready').bind('desktop',now(),body.ready===true?1:0,JSON.stringify(modes),body.conversationReady===true?1:0,body.sourcesReady===true?1:0,body.critiqueReady===true?1:0,body.examReady===true?1:0,body.screenshotReady===true?1:0,body.essayReady===true?1:0).run();
      return json({ok:true});
    }
    if (body.action === 'claim') {
      await expireJobs();
      await expireCritiques();
      const job = await database().prepare(CLAIM_SQL).bind(crypto.randomUUID(),now()).first();
      return json({job});
    }
    if(body.action==='screenshotRead'&&validId(body.id)&&validId(body.lease)){
      const job=await database().prepare("SELECT screenshot_json FROM textbook_jobs WHERE id=? AND status='running' AND lease=? AND leased_at>=? AND task_type IN ('exam','recognize')").bind(body.id,body.lease,now()-240).first<{screenshot_json:string}>();
      if(!job)return json({error:'Late image request'},409);
      const manifest=parseManifest(job.screenshot_json),images=[];
      for(const image of manifest.images){const object=await runtime().BUCKET?.get(image.key);if(!object)return json({error:'Screenshot unavailable'},503);const bytes=new Uint8Array(await object.arrayBuffer()),info=pngInfo(bytes),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');if(bytes.length!==image.size||info.width!==image.width||info.height!==image.height||sha!==image.sha)return json({error:'Screenshot integrity mismatch'},503);let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));images.push({dataUrl:'data:image/png;base64,'+btoa(binary),width:image.width,height:image.height});}
      return json({images});
    }
    if(body.action==='recognitionComplete'&&validId(body.id)&&validId(body.lease)){
      let recognized=null;try{if(body.recognition!=null)recognized=validateRecognition(body.recognition);}catch{return json({error:'Invalid recognition'},400);}
      if(!recognized&&typeof body.error!=='string')return json({error:'Empty recognition'},400);
      const changed=await database().prepare("UPDATE textbook_jobs SET status=?,answer=?,recognition_json=?,error=?,completed_at=?,lease=NULL WHERE id=? AND task_type='recognize' AND status='running' AND lease=? AND leased_at>=? RETURNING id").bind(recognized?'done':'failed',recognized?.question??null,recognized?JSON.stringify(recognized):null,recognized?null:'截图识别失败或超时，请裁剪清晰图片后重试。',now(),body.id,body.lease,now()-240).first();
      return json({ok:Boolean(changed)},changed?200:409);
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
      const refs=references(body.references);
      const job=await database().prepare("SELECT task_type,cancel_requested FROM textbook_jobs WHERE id=? AND status='running' AND lease=? AND leased_at>=?").bind(body.id,body.lease,now()-240).first<{task_type:string;cancel_requested:number}>();
      if(!job)return json({error:'Late result'},409);
      if(job.cancel_requested===1){const stopped=await database().prepare(STOPPED_SQL).bind(now(),body.id,body.lease,now()-240).first();return json({ok:Boolean(stopped)},stopped?200:409);}
      if(job.task_type==='recognize')return json({error:'Wrong task result type'},400);
      const diagnostic=rewriteDiagnostic(body,job.task_type==='case'?6000:2000);
      let practice=null;
      try{if(answer&&job.task_type==='exam')practice=validatePractice(body.practice,refs.map(r=>r.rank));else if(body.practice!=null)return json({error:'Unexpected practice'},400);}catch{return json({error:'Invalid practice'},400);}
      const changed = await database().prepare(COMPLETE_SQL).bind(answer?'done':'failed',answer||null,error||null,now(),Math.max(0,Math.min(240000,Number(body.elapsedMs)||0)),diagnostic.query,diagnostic.route,JSON.stringify(refs),practice?JSON.stringify(practice):null,body.id,body.lease,now()-240).first();
      return json({ok:Boolean(changed)},changed?200:409);
    }
    return json({error:'Invalid action'},400);
  } catch (error) {
    console.error('textbook bridge',error instanceof Error ? error.name : 'error');
    return json({error:'Bridge temporarily unavailable'},503);
  }
}
