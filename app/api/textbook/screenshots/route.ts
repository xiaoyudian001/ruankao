import {owner,sameOrigin,json,now,database,runtime,bridgeState,expireJobs} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {boundedUpload,pngInfo,parseManifest,validateRecognition,type ScreenshotManifest} from '../../../../lib/textbook/screenshots';

export async function GET(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  const u=new URL(request.url),id=u.searchParams.get('id');if(!validId(id))return json({error:'截图标识无效。'},400);
  await expireJobs();const job=await database().prepare("SELECT id,status,error,screenshot_json,recognition_json FROM textbook_jobs WHERE id=? AND owner_id=? AND task_type='recognize'").bind(id,user.userId).first<{id:string;status:string;error:string|null;screenshot_json:string;recognition_json:string|null}>();
  if(!job)return json({error:'截图任务不存在。'},404);
  const manifest=parseManifest(job.screenshot_json),image=u.searchParams.get('image');
  if(image!=null){const index=Number(image);if(!Number.isInteger(index)||!manifest.images[index])return json({error:'截图不存在。'},404);const object=await runtime().BUCKET?.get(manifest.images[index].key);if(!object)return json({error:'截图暂不可用。'},404);return new Response(object.body,{headers:{'Content-Type':'image/png','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});}
  return json({id:job.id,status:job.status,error:job.error,recognition:job.recognition_json?validateRecognition(JSON.parse(job.recognition_json)):null,imageCount:manifest.images.length});
 }catch{return json({error:'截图暂时无法读取，请稍后重试。'},503);}
}

export async function POST(request:Request){
 let savedKeys:string[]=[];
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  const form=await boundedUpload(request),id=form.get('requestId'),files=form.getAll('images');
  if(!validId(id)||!files.length||files.length>2)return json({error:'每次请选择一道题，最多两张截图。'},400);
  const images=[];const content:Uint8Array[]=[];
  for(const [i,file] of files.entries()){
   if(!(file instanceof File)||file.type!=='image/png'||file.size>2*1024*1024)return json({error:'请上传 PNG 截图，每张不超过 2 MB。'},400);
   const bytes=new Uint8Array(await file.arrayBuffer()),info=pngInfo(bytes),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
   images.push({...info,size:bytes.length,sha,key:`exam-screenshots/${id}/${i}-${sha}.png`});content.push(bytes);
  }
  const manifest:ScreenshotManifest={recognitionId:id,images},serialized=JSON.stringify(manifest),db=database();
  const prior=await db.prepare('SELECT id,owner_id,screenshot_json,status FROM textbook_jobs WHERE id=?').bind(id).first<{id:string;owner_id:string;screenshot_json:string;status:string}>();
  if(prior){if(prior.owner_id!==user.userId||prior.screenshot_json!==serialized)return json({error:'请求标识已用于其他截图。'},409);return json({id,status:prior.status});}
  const connection=await bridgeState();if(!connection.screenshotReady)return json({error:'截图识题尚未连接，请启动教材问答连接后重试。'},503);
  await expireJobs();const bucket=runtime().BUCKET;if(!bucket)throw new Error('Storage unavailable');
  for(const [i,image] of images.entries()){await bucket.put(image.key,content[i],{httpMetadata:{contentType:'image/png'}});savedKeys.push(image.key);}
  const session=crypto.randomUUID();
  const results=await db.batch([
   db.prepare('INSERT INTO textbook_sessions (id,owner_id,title,created_at,updated_at) VALUES (?,?,?,?,?)').bind(session,user.userId,'截图识题',now(),now()),
   db.prepare("INSERT OR IGNORE INTO textbook_jobs (id,session_id,owner_id,question,status,created_at,task_type,screenshot_json) SELECT ?,?,?,?,'queued',?,'recognize',? WHERE (SELECT COUNT(*) FROM textbook_jobs WHERE status IN ('queued','running'))<3").bind(id,session,user.userId,'识别题目截图',now(),serialized),
  ]);
  if(!results[1].meta.changes){const existing=await db.prepare('SELECT owner_id,screenshot_json,status FROM textbook_jobs WHERE id=?').bind(id).first<{owner_id:string;screenshot_json:string;status:string}>();const retained=existing?.screenshot_json?parseManifest(existing.screenshot_json).images.map(x=>x.key):[];await Promise.all(savedKeys.filter(k=>!retained.includes(k)).map(k=>bucket.delete(k)));savedKeys=[];if(existing?.owner_id===user.userId&&existing.screenshot_json===serialized)return json({id,status:existing.status});return json({error:'已有任务正在处理，请稍后再识别。'},409);}
  return json({id,status:'queued'},202);
 }catch(e){
  // Do not delete content after a database timeout: its INSERT may already have succeeded.
  if(e instanceof Error&&/截图|PNG|裁剪/.test(e.message))return json({error:e.message},400);
  return json({error:'截图上传失败，图片已保留，请重试。'},503);
 }
}
