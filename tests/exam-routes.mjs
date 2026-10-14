// Execute actual route handlers with transactional SQLite and an isolated auth/runtime adapter.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
const root=process.cwd(),dir=path.join(root,'outputs','exam-route-test');fs.mkdirSync(dir,{recursive:true});
const url=f=>pathToFileURL(path.join(root,f)).href;
const serverSource=fs.readFileSync('lib/textbook/server.ts','utf8');
const sql=name=>serverSource.match(new RegExp('export const '+name+' = `([\\s\\S]*?)`;'))?.[1];
const stub=path.join(dir,'server.mjs');
fs.writeFileSync(stub,`
import {DatabaseSync} from 'node:sqlite';
export const sqlite=new DatabaseSync(':memory:');
export let user='owner';export function signIn(v){user=v;}
export async function owner(){return user?{userId:user}:null;}
export const now=()=>Math.floor(Date.now()/1000);
export const json=(data,status=200)=>Response.json(data,{status});
export const sameOrigin=r=>r.headers.get('origin')==='http://localhost:5173';
export const bridgeAuth=r=>r.headers.get('authorization')==='Bearer local-test';
export async function expireJobs(){}
function statement(sql,args=[]){return {bind:(...a)=>statement(sql,a),first:async()=>sqlite.prepare(sql).get(...args)??null,all:async()=>({results:sqlite.prepare(sql).all(...args)}),run:async()=>({meta:sqlite.prepare(sql).run(...args)})};}
const db={prepare:statement,batch:async statements=>{sqlite.exec('BEGIN');try{const results=[];for(const s of statements)results.push(await s.run());sqlite.exec('COMMIT');return results;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
export const database=()=>db;
export const objects=new Map();
export const runtime=()=>({BUCKET:{put:async(k,b)=>objects.set(k,new Uint8Array(b)),delete:async k=>objects.delete(k),get:async k=>{const b=objects.get(k);return b?{body:b,arrayBuffer:async()=>b.buffer}:null;}}});
export async function bridgeState(){const s=sqlite.prepare('SELECT * FROM textbook_bridge').get();return {online:s?.ready===1,availableModes:s?.ready===1?['default','complete']:[],conversationReady:true,examReady:s?.exam_ready===1,screenshotReady:s?.screenshot_ready===1};}
export const CLAIM_SQL=${JSON.stringify(sql('CLAIM_SQL'))};
export const COMPLETE_SQL=${JSON.stringify(sql('COMPLETE_SQL'))};
export const HISTORY_SQL=${JSON.stringify(sql('HISTORY_SQL'))};
`);
function compile(file,changes){let code=fs.readFileSync(file,'utf8');for(const [from,to] of Object.entries(changes))code=code.replaceAll(from,to);const target=path.join(dir,file.replaceAll('/','-').replace('.ts','.mjs'));fs.writeFileSync(target,ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);return pathToFileURL(target).href;}
const serverUrl=pathToFileURL(stub).href;
const sessionsUrl=compile('lib/textbook/sessions.ts',{"'./server'":JSON.stringify(serverUrl)});
const critiqueServer=compile('lib/review/critique-server.ts',{'../textbook/server':serverUrl,'../textbook/sources':url('lib/textbook/sources.ts'),'./critique':url('lib/review/critique.ts')});
const shared={'../../../../lib/textbook/token-usage':url('lib/textbook/token-usage.ts'),'../../../../lib/textbook/screenshots':url('lib/textbook/screenshots.ts'),'../../../../lib/textbook/server':serverUrl,'../../../../lib/textbook/policy':url('lib/textbook/policy.ts'),'../../../../lib/textbook/sources':url('lib/textbook/sources.ts'),'../../../../lib/textbook/conversation':url('lib/textbook/conversation.ts'),'../../../../lib/textbook/exam':url('lib/textbook/exam.ts'),'../../../../lib/review/critique-server':critiqueServer,'../../../../lib/review/critique':url('lib/review/critique.ts')};
const chat=await import(compile('app/api/textbook/chat/route.ts',{...shared,'../../../../lib/textbook/sessions':sessionsUrl,'../../../../lib/textbook/answer-actions':url('lib/textbook/answer-actions.ts')}));
const bridge=await import(compile('app/api/textbook/bridge/route.ts',{...shared,'../../../../lib/textbook/streaming':url('lib/textbook/streaming.ts')}));
const exam=await import(compile('app/api/textbook/exam/route.ts',shared));
const state=await import(serverUrl),db=state.sqlite;
for(const file of fs.readdirSync('drizzle').filter(n=>n.endsWith('.sql')).sort())db.exec(fs.readFileSync(path.join('drizzle',file),'utf8'));
const post=async(route,endpoint,body,headers={})=>{const r=await route.POST(new Request('http://localhost:5173/api/textbook/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json',Origin:'http://localhost:5173',...headers},body:JSON.stringify(body)}));return {status:r.status,data:await r.json()};};
const auth={Authorization:'Bearer local-test'};
const body={requestId:crypto.randomUUID(),question:'MTBF含义？\nA.间隔 B.修复 C.成本 D.速度',taskType:'exam',retrievalMode:'default'};
assert.equal((await post(chat,'chat',body)).status,503);
await post(bridge,'bridge',{action:'heartbeat',ready:true,modes:['default','complete'],examReady:false},auth);
assert.equal((await post(chat,'chat',body)).status,503);
await post(bridge,'bridge',{action:'heartbeat',ready:true,modes:['default','complete'],examReady:true},auth);
state.signIn(null);assert.equal((await post(chat,'chat',body)).status,403);state.signIn('owner');
assert.equal((await post(chat,'chat',body,{Origin:'https://evil.example'})).status,403);
assert.equal((await post(chat,'chat',{...body,taskType:'evil'})).status,400);
const queued=await post(chat,'chat',body);assert.equal(queued.status,202);
const recover=async id=>await (await chat.GET(new Request('http://localhost:5173/api/textbook/chat?requestId='+id))).json();
let restored=await recover(body.requestId);assert.equal(restored.selectedSessionId,queued.data.job.session_id);assert.equal(restored.messages[0].status,'queued');assert.ok(Number.isInteger(restored.serverNow));assert.equal(restored.messages[0].leased_at,null);
state.signIn('other');assert.equal((await recover(body.requestId)).selectedSessionId,null);state.signIn('owner');
assert.equal((await post(chat,'chat',body)).status,200);
assert.equal(db.prepare('SELECT COUNT(*) AS n FROM textbook_jobs WHERE id=?').get(body.requestId).n,1);
assert.equal((await post(chat,'chat',{...body,taskType:'qa'})).status,409);
const job=(await post(bridge,'bridge',{action:'claim'},auth)).data.job;assert.equal(job.task_type,'exam');assert.equal(job.history_json,'[]');
restored=await recover(body.requestId);assert.equal(restored.messages[0].status,'running');assert.ok(restored.messages[0].leased_at>0);
const refs=[{rank:1,bookSha:'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9',chunkId:'a'.repeat(64),content:'MTBF为平均故障间隔时间。',pdfPages:[323],label:'教材308页（PDF323页）',chapter:'第9章'}];
const practice={question:'故障间隔缩写？',options:[{label:'A',text:'MTBF'},{label:'B',text:'MTTR'},{label:'C',text:'ROI'},{label:'D',text:'DPI'}],correct:'A',explanation:'MTBF是平均故障间隔。[片段1]',ranks:[1]};
const done={action:'complete',id:job.id,lease:job.lease,answer:'答案A [片段1]',references:refs,practice,retrievalQuery:body.question.replace(/\n/g,' '),rewriteRoute:'direct'};
assert.equal((await post(bridge,'bridge',{...done,practice:{...practice,ranks:[9]}},auth)).status,400);
assert.equal((await post(bridge,'bridge',{...done,lease:crypto.randomUUID()},auth)).status,409);
assert.equal((await post(bridge,'bridge',done,auth)).status,200);
const get=async()=>{const r=await chat.GET(new Request('http://localhost:5173/api/textbook/chat?sessionId='+queued.data.job.session_id));return r.json();};
let history=await get();assert.equal(history.messages[0].task_type,'exam');assert.deepEqual(Object.keys(history.messages[0].practice).sort(),['options','question']);assert.ok(!JSON.stringify(history).includes('explanation'));
restored=await recover(body.requestId);assert.equal(restored.messages[0].status,'done');assert.ok(restored.messages[0].leased_at>0);
state.signIn('other');assert.equal((await post(exam,'exam',{jobId:job.id,choice:'A'})).status,404);state.signIn('owner');
assert.equal((await post(exam,'exam',{jobId:job.id,choice:'A'},{Origin:'https://evil.example'})).status,403);
assert.equal((await post(exam,'exam',{jobId:job.id,choice:'Z'})).status,400);
let result=await post(exam,'exam',{jobId:job.id,choice:'B'});assert.equal(result.status,200);assert.equal(result.data.practice.isCorrect,false);assert.equal(result.data.practice.correct,'A');
assert.equal((await post(exam,'exam',{jobId:job.id,choice:'B'})).status,200);assert.equal((await post(exam,'exam',{jobId:job.id,choice:'A'})).status,409);
history=await get();assert.equal(history.messages[0].practice.choice,'B');assert.equal(history.messages[0].practice.explanation,practice.explanation);
const caseJob=crypto.randomUUID(),caseLease=crypto.randomUUID(),caseSession=crypto.randomUUID();
db.prepare('INSERT INTO textbook_sessions VALUES(?,?,?,?,?)').run(caseSession,'owner','隐藏案例分析',state.now(),state.now());
db.prepare("INSERT INTO textbook_jobs(id,session_id,owner_id,question,status,created_at,task_type,lease,leased_at) VALUES(?,?,?,?,'running',?,'case',?,?)").run(caseJob,caseSession,'owner','背景'.repeat(1800)+'当前小问',state.now(),caseLease,state.now());
assert.equal((await post(bridge,'bridge',{action:'complete',id:caseJob,lease:caseLease,answer:'案例参考[片段1]',references:refs,practice:null,retrievalQuery:'背景'.repeat(1800)+'当前小问',rewriteRoute:'direct'},auth)).status,200);
const hidden=await (await chat.GET(new Request('http://localhost:5173/api/textbook/chat?sessionId='+caseSession))).json();assert.equal(hidden.messages.length,0);assert.ok(!hidden.sessions.some(s=>s.id===caseSession));
assert.equal((await recover(caseJob)).selectedSessionId,null);
console.log(JSON.stringify({passed:true,checks:['owner','origin','readiness','idempotency','task_type','claim','valid_sources','lease','hidden_solution','atomic_choice','saved_reload']}));
