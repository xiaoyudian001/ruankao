import {BOOK_SHA,selectedReference} from '../../../../lib/textbook/sources';
import {bridgeState,database,json,now,owner,runtime,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';

async function resolve(userId:string,jobId:unknown,rank:unknown,page:unknown){
  if(!validId(jobId))return null;
  const job=await database().prepare("SELECT references_json FROM textbook_jobs WHERE id=? AND owner_id=? AND status='done'").bind(jobId,userId).first<{references_json:string}>();
  return job?selectedReference(job.references_json,rank,page):null;
}
type PageState={status:string;error:string|null;file_key:string|null;updated_at:number};
const pageState=(page:number)=>database().prepare('SELECT status,error,file_key,updated_at FROM textbook_pages WHERE page=?').bind(page).first<PageState>();

export async function POST(request:Request){
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  try{
    const raw=await request.text();if(raw.length>1000)return json({error:'请求过长。'},400);
    const body=JSON.parse(raw);
    const reference=await resolve(user.userId,body.jobId,body.rank,body.page);
    if(!reference)return json({error:'该回答未保存此引用，或页码不在引用范围内。'},404);
    const page=Number(body.page);let state=await pageState(page);
    if(state?.status!=='ready'){
      const connection=await bridgeState();
      if(!connection.sourcesReady)return json({reference,page,status:'offline',error:'电脑未连接原页服务；连接恢复后点击重试。'});
      await database().prepare(`INSERT INTO textbook_pages (page,status,created_at,updated_at)
        SELECT ?,'queued',?,? WHERE (SELECT COUNT(*) FROM textbook_pages WHERE status IN ('queued','running'))<8
        ON CONFLICT(page) DO UPDATE SET status='queued',error=NULL,lease=NULL,updated_at=excluded.updated_at
        WHERE textbook_pages.status='failed' OR (textbook_pages.status IN ('queued','running') AND textbook_pages.updated_at<?)`).bind(page,now(),now(),now()-90).run();
      state=await pageState(page);
      if(!state)return json({reference,page,status:'failed',error:'原页队列繁忙，请稍后重试。'});
    }
    return json({reference,page,status:state.status,error:state.error});
  }catch{return json({error:'引用暂时无法读取，请重试。'},503);}
}

export async function GET(request:Request){
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  try{
    const q=new URL(request.url).searchParams;const page=Number(q.get('page'));
    const reference=await resolve(user.userId,q.get('jobId'),Number(q.get('rank')),page);
    if(!reference)return json({error:'引用不存在。'},404);
    const state=await pageState(page);
    if(state?.status==='ready'&&state.file_key?.startsWith('textbook/'+BOOK_SHA+'/')){
      const image=await runtime().BUCKET?.get(state.file_key);
      if(image)return new Response(image.body,{headers:{'Content-Type':'image/jpeg','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin'}});
      await database().prepare("UPDATE textbook_pages SET status='failed',error=? WHERE page=? AND file_key=?").bind('页面缓存失效，请重试。',page,state.file_key).run();
      return json({status:'failed',error:'页面缓存失效，请重试。'},409);
    }
    if(state&&(state.status==='queued'||state.status==='running')&&state.updated_at<now()-90)return json({status:'failed',error:'页面准备超时，请重试。'},409);
    return json({status:state?.status??'failed',error:state?.error??null},state?.status==='failed'?409:202);
  }catch{return json({error:'原页暂时无法读取。'},503);}
}
