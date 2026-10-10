import {database,json,now,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {sourceSummaries} from '../../../../lib/textbook/sources';
import {cardText,scheduleReview,studyDate} from '../../../../lib/review/model';
import {REVIEW_INSERT_SQL,REVIEW_UPDATE_SQL} from '../../../../lib/review/store';
import {critiqueSummary,expireCritiques} from '../../../../lib/review/critique-server';

export async function GET(request:Request){
  try{
    const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
    const db=database();const today=studyDate();const view=new URL(request.url).searchParams.get('view');
    if(view==='favorites'){
      const favorites=await db.prepare('SELECT job_id FROM textbook_favorites WHERE owner_id=? ORDER BY created_at DESC LIMIT 200').bind(user.userId).all();return json({favorites:favorites.results});
    }
    if(view==='summary'){
      const [cards,reviews]=await Promise.all([
        db.prepare('SELECT COUNT(*) AS cards,COALESCE(SUM(CASE WHEN due_date<=? THEN 1 ELSE 0 END),0) AS due FROM textbook_cards WHERE owner_id=?').bind(today,user.userId).first(),
        db.prepare('SELECT COUNT(DISTINCT card_id) AS done FROM textbook_reviews WHERE owner_id=? AND study_date=?').bind(user.userId,today).first(),
      ]);return json({...cards,...reviews,today});
    }
    await expireCritiques();
    const [favorites,cards,reviews,stats]=await Promise.all([
      db.prepare('SELECT * FROM textbook_favorites WHERE owner_id=? ORDER BY created_at DESC,rowid DESC LIMIT 200').bind(user.userId).all(),
      db.prepare('SELECT c.*,f.job_id,f.references_json FROM textbook_cards c JOIN textbook_favorites f ON f.id=c.favorite_id AND f.owner_id=c.owner_id WHERE c.owner_id=? ORDER BY c.due_date,c.created_at LIMIT 200').bind(user.userId).all(),
      db.prepare(`SELECT r.id,r.card_id,r.grade,r.response,r.study_date,r.due_date,r.created_at,q.id AS critique_id,q.status,q.result_json,q.error,q.references_json
        FROM textbook_reviews r LEFT JOIN textbook_critiques q ON q.id=r.critique_id AND q.owner_id=r.owner_id
        WHERE r.owner_id=? ORDER BY r.created_at DESC,r.rowid DESC LIMIT 2000`).bind(user.userId).all(),
      db.prepare('SELECT study_date,COUNT(DISTINCT card_id) AS cards,COUNT(*) AS attempts FROM textbook_reviews WHERE owner_id=? GROUP BY study_date').bind(user.userId).all(),
    ]);
    const summarize=(r:Record<string,unknown>)=>{const {owner_id,references_json,last_review_id,...data}=r;return {...data,references:sourceSummaries(references_json)};};
    const events=reviews.results.map(r=>{const {critique_id,status,result_json,error,references_json,...event}=r;return {...event,critique:critique_id?critiqueSummary({id:critique_id,status,result_json,error,references_json}):null};});
    return json({favorites:favorites.results.map(summarize),cards:cards.results.map(summarize),reviews:events,stats:stats.results,today});
  }catch{return json({error:'复习内容暂时无法读取，请重试。'},503);}
}

export async function POST(request:Request){
  try{
    const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
    if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
    const raw=await request.text();if(raw.length>40000)return json({error:'内容过长。'},400);
    const b=JSON.parse(raw) as Record<string,unknown>;const db=database();const ownerId=user.userId;const timestamp=now();
    if(b.action==='favorite'){
      if(!validId(b.jobId))return json({error:'回答标识无效。'},400);
      // Copy only trusted, completed server content. The browser cannot replace evidence.
      const job=await db.prepare("SELECT question,retrieval_query,answer,references_json,rewrite_route FROM textbook_jobs WHERE id=? AND owner_id=? AND status='done'").bind(b.jobId,ownerId).first<{question:string;retrieval_query:string|null;answer:string|null;references_json:string;rewrite_route:string|null}>();
      if(!job?.answer||job.rewrite_route==='clarification')return json({error:'这条回答还不能收藏。'},400);
      await db.prepare(`INSERT OR IGNORE INTO textbook_favorites (id,owner_id,job_id,question,retrieval_query,answer,references_json,created_at)
        SELECT ?,?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM textbook_favorites WHERE owner_id=?)<200`).bind(crypto.randomUUID(),ownerId,b.jobId,job.question,job.retrieval_query,job.answer,job.references_json,timestamp,ownerId).run();
      const favorite=await db.prepare('SELECT id FROM textbook_favorites WHERE owner_id=? AND job_id=?').bind(ownerId,b.jobId).first();
      return favorite?json({favorite}):json({error:'收藏已达到 200 条。'},409);
    }
    if(b.action==='card'){
      if(!validId(b.favoriteId))return json({error:'收藏标识无效。'},400);
      const favorite=await db.prepare('SELECT id FROM textbook_favorites WHERE id=? AND owner_id=?').bind(b.favoriteId,ownerId).first();
      if(!favorite)return json({error:'收藏不存在。'},404);
      const front=cardText(b.front,2000),back=cardText(b.back,20000);
      await db.prepare('INSERT OR IGNORE INTO textbook_cards (id,owner_id,favorite_id,front,back,due_date,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)').bind(crypto.randomUUID(),ownerId,b.favoriteId,front,back,studyDate(),timestamp,timestamp).run();
      const card=await db.prepare('SELECT id,front,back FROM textbook_cards WHERE favorite_id=? AND owner_id=?').bind(b.favoriteId,ownerId).first<{id:string;front:string;back:string}>();
      return card?.front===front&&card?.back===back?json({card}):json({error:'此收藏已经制成卡片，请刷新后编辑已有卡片。'},409);
    }
    if(b.action==='edit'){
      if(!validId(b.cardId)||!Number.isInteger(b.version)||Number(b.version)<0)return json({error:'卡片标识或版本无效。'},400);
      const front=cardText(b.front,2000),back=cardText(b.back,20000);
      const result=await db.prepare('UPDATE textbook_cards SET front=?,back=?,version=version+1,updated_at=? WHERE id=? AND owner_id=? AND version=?').bind(front,back,timestamp,b.cardId,ownerId,b.version).run();
      return result.meta.changes?json({saved:true}):json({error:'卡片已在其他窗口更新，请刷新后重试。'},409);
    }
    if(b.action==='review'){
      if(!validId(b.cardId)||!validId(b.requestId)||!Number.isInteger(b.version)||Number(b.version)<0)return json({error:'练习标识或版本无效。'},400);
      if(typeof b.response!=='string'||b.response.length>5000)return json({error:'回忆内容最多 5000 字。'},400);
      scheduleReview(0,b.grade); // Validate grade before either first write or retry.
      if(b.critiqueId!=null&&!validId(b.critiqueId))return json({error:'点评标识无效。'},400);
      type Event={id:string;card_id:string;grade:string;response:string;card_version:number;due_date:string;critique_id:string|null};
      const previous=await db.prepare('SELECT * FROM textbook_reviews WHERE id=? AND owner_id=?').bind(b.requestId,ownerId).first<Event>();
      const matches=(e:Event)=>e.card_id===b.cardId&&e.grade===b.grade&&e.response===b.response&&e.card_version===Number(b.version)+1&&e.critique_id===(b.critiqueId??null);
      if(previous)return matches(previous)?json({review:previous}):json({error:'请求标识已用于其他练习。'},409);
      const card=await db.prepare('SELECT streak,version FROM textbook_cards WHERE id=? AND owner_id=?').bind(b.cardId,ownerId).first<{streak:number;version:number}>();
      if(!card)return json({error:'卡片不存在。'},404);
      if(card.version!==b.version)return json({error:'卡片已在其他窗口更新，请刷新后重试。'},409);
      if(b.critiqueId){const q=await db.prepare('SELECT id FROM textbook_critiques WHERE id=? AND owner_id=? AND card_id=? AND card_version=? AND response=?').bind(b.critiqueId,ownerId,b.cardId,b.version,b.response).first();if(!q)return json({error:'点评与本次回忆不匹配。'},409);}
      const today=studyDate(),next=scheduleReview(card.streak,b.grade,today);
      await db.batch([
        db.prepare(REVIEW_UPDATE_SQL).bind(next.streak,next.dueDate,b.requestId,timestamp,b.cardId,ownerId,b.version,b.requestId),
        db.prepare(REVIEW_INSERT_SQL).bind(b.requestId,b.grade,b.response,today,next.dueDate,Number(b.version)+1,timestamp,b.cardId,ownerId,b.requestId,Number(b.version)+1),
        db.prepare('UPDATE textbook_reviews SET critique_id=? WHERE id=? AND owner_id=? AND critique_id IS NULL').bind(b.critiqueId??null,b.requestId,ownerId),
      ]);
      const event=await db.prepare('SELECT * FROM textbook_reviews WHERE id=? AND owner_id=?').bind(b.requestId,ownerId).first<Event>();
      return event&&matches(event)?json({review:event}):json({error:'这张卡片刚刚已被更新，请刷新后再练。'},409);
    }
    return json({error:'操作无效。'},400);
  }catch(error){
    if(error instanceof SyntaxError)return json({error:'提交内容格式无效。'},400);
    if(error instanceof Error&&(error.message.startsWith('请填写')||error.message.startsWith('请选择')))return json({error:error.message},400);
    return json({error:'保存失败，内容已保留，请重试。'},503);
  }
}
