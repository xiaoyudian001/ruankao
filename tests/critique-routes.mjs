// Execute real route handlers against transactional in-memory SQLite. No production data.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
const root=process.cwd(),dir=path.join(root,'outputs','critique-route-test');fs.mkdirSync(dir,{recursive:true});
const url=f=>pathToFileURL(path.join(root,f)).href;
const stub=path.join(dir,'server.mjs');
fs.writeFileSync(stub,`
import {DatabaseSync} from 'node:sqlite';
export const sqlite=new DatabaseSync(':memory:');
export let loggedIn=true;export function signIn(value){loggedIn=value;}
export async function owner(){return loggedIn?{userId:'owner'}:null;}
export const now=()=>Math.floor(Date.now()/1000);
export const json=(data,status=200)=>Response.json(data,{status});
export const sameOrigin=r=>r.headers.get('origin')==='http://localhost:5173';
export const bridgeAuth=r=>r.headers.get('authorization')==='Bearer local-test';
export async function expireJobs(){}
function statement(sql,args=[]){return {bind:(...a)=>statement(sql,a),first:async()=>sqlite.prepare(sql).get(...args)??null,all:async()=>({results:sqlite.prepare(sql).all(...args)}),run:async()=>({meta:sqlite.prepare(sql).run(...args)})};}
const db={prepare:statement,batch:async statements=>{sqlite.exec('BEGIN');try{const results=[];for(const s of statements)results.push(await s.run());sqlite.exec('COMMIT');return results;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
export const database=()=>db;export const runtime=()=>({});
export async function bridgeState(){const b=sqlite.prepare('SELECT critique_ready FROM textbook_bridge').get();return {critiqueReady:b?.critique_ready===1};}
export const CLAIM_SQL='SELECT 1';export const COMPLETE_SQL='SELECT 1';
`);
function compile(file,changes){let code=fs.readFileSync(path.join(root,file),'utf8');for(const [from,to] of Object.entries(changes))code=code.replaceAll(from,to);const target=path.join(dir,path.basename(file).replace('.ts','.mjs').replace('route.mjs',file.split('/')[3]+'-route.mjs'));fs.writeFileSync(target,ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);return pathToFileURL(target).href;}
const serverUrl=pathToFileURL(stub).href;
const critiqueServer=compile('lib/review/critique-server.ts',{'../textbook/server':serverUrl,'../textbook/sources':url('lib/textbook/sources.ts'),'./critique':url('lib/review/critique.ts')});
const shared={'../../../../lib/textbook/screenshots':url('lib/textbook/screenshots.ts'),'../../../../lib/textbook/exam':url('lib/textbook/exam.ts'),'../../../../lib/textbook/server':serverUrl,'../../../../lib/textbook/policy':url('lib/textbook/policy.ts'),'../../../../lib/textbook/sources':url('lib/textbook/sources.ts'),'../../../../lib/textbook/conversation':url('lib/textbook/conversation.ts'),'../../../../lib/review/critique-server':critiqueServer,'../../../../lib/review/critique':url('lib/review/critique.ts'),'../../../../lib/review/model':url('lib/review/model.ts'),'../../../../lib/review/store':url('lib/review/store.ts')};
const critique=await import(compile('app/api/textbook/critique/route.ts',shared));
const bridge=await import(compile('app/api/textbook/bridge/route.ts',shared));
const review=await import(compile('app/api/textbook/review/route.ts',shared));
const state=await import(serverUrl),db=state.sqlite;
for(const migration of fs.readdirSync(path.join(root,'drizzle')).filter(n=>n.endsWith('.sql')).sort())db.exec(fs.readFileSync(path.join(root,'drizzle',migration),'utf8'));
const owner='owner',cardId=crypto.randomUUID(),favoriteId=crypto.randomUUID(),jobId=crypto.randomUUID(),tsNow=state.now();
const refs=[{rank:1,bookSha:'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9',chunkId:'a'.repeat(64),content:'MTBF定义为平均故障间隔时间；MTTR为平均恢复前时间。',pdfPages:[323],label:'教材308页（PDF323页）',chapter:'第9章'}];
db.prepare('INSERT INTO textbook_favorites VALUES(?,?,?,?,?,?,?,?)').run(favoriteId,owner,jobId,'问题',null,'真实原答案',JSON.stringify(refs),tsNow);
db.prepare('INSERT INTO textbook_cards(id,owner_id,favorite_id,front,back,due_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)').run(cardId,owner,favoriteId,'MTBF与MTTR区别','卡片参考答案','2026-10-10',tsNow,tsNow);
const request=(endpoint,body,headers={})=>new Request('http://localhost:5173/api/textbook/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json',Origin:'http://localhost:5173',...headers},body:JSON.stringify(body)});
async function post(route,endpoint,body,headers){const r=await route.POST(request(endpoint,body,headers));return {status:r.status,data:await r.json()};}
const response='MTTR是故障间隔时间 "混淆"\n路径 C:\\笔记\\notes';
const payload={cardId,version:0,response,requestId:crypto.randomUUID(),back:'浏览器伪造答案',references_json:'伪造片段'};
assert.equal((await post(critique,'critique',payload)).status,503);
state.signIn(false);assert.equal((await post(critique,'critique',payload)).status,403);state.signIn(true);
assert.equal((await post(critique,'critique',payload,{Origin:'https://bad.example'})).status,403);
assert.equal((await post(bridge,'bridge',{action:'heartbeat',critiqueReady:true})).status,401);
assert.equal((await post(bridge,'bridge',{action:'heartbeat',ready:true,critiqueReady:true},{Authorization:'Bearer local-test'})).status,200);
let result=await post(critique,'critique',payload);assert.equal(result.status,202);const id=result.data.critique.id;
const snapshot=db.prepare('SELECT * FROM textbook_critiques WHERE id=?').get(id);assert.equal(snapshot.back,'卡片参考答案');assert.equal(snapshot.references_json,JSON.stringify(refs));assert.equal(snapshot.response,response);
assert.equal((await post(critique,'critique',payload)).data.critique.id,id);
assert.equal((await post(critique,'critique',{...payload,requestId:crypto.randomUUID()})).data.critique.id,id);
assert.equal((await post(critique,'critique',{...payload,response:'changed'})).status,409);
result=await post(bridge,'bridge',{action:'critiqueClaim'},{Authorization:'Bearer local-test'});assert.equal(result.status,200);const task=result.data.critique;assert.equal(task.id,id);
const feedback={summary:'定义混淆',correct:[],missing:[],corrections:[{point:'MTTR应为平均恢复前时间',ranks:[1]}],suggestion:'对照两者定义',insufficientEvidence:false};
assert.equal((await post(bridge,'bridge',{action:'critiqueComplete',id,lease:task.lease,result:{...feedback,corrections:[{point:'编造',ranks:[9]}]}},{Authorization:'Bearer local-test'})).status,400);
assert.equal((await post(bridge,'bridge',{action:'critiqueComplete',id,lease:crypto.randomUUID(),result:feedback},{Authorization:'Bearer local-test'})).status,409);
assert.equal((await post(bridge,'bridge',{action:'critiqueComplete',id,lease:task.lease,result:feedback},{Authorization:'Bearer local-test'})).status,200);
assert.equal((await critique.GET(new Request('http://localhost:5173/api/textbook/critique?id='+id))).status,200);
const grade={action:'review',cardId,version:0,requestId:crypto.randomUUID(),grade:'partial',response,critiqueId:id};
assert.equal((await post(review,'review',{...grade,response:'mismatch'})).status,409);
assert.equal((await post(review,'review',grade)).status,200);assert.equal((await post(review,'review',grade)).status,200);
const history=await (await review.GET(new Request('http://localhost:5173/api/textbook/review'))).json();assert.equal(history.reviews[0].critique.result.corrections[0].ranks[0],1);
console.log(JSON.stringify({passed:true,checks:['offline','owner','origin','bridge_auth','trusted_snapshot','escape_roundtrip','request_idempotency','pending_deduplication','valid_ranks','lease','review_matching','history_persistence']}));
