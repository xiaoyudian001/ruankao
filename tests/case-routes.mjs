// Real handlers and migrations against isolated SQLite. No network or model call.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
const dir=path.resolve('outputs/case-route-test');fs.mkdirSync(dir,{recursive:true});
const url=f=>pathToFileURL(path.resolve(f)).href;
const stub=path.join(dir,'server.mjs');
fs.writeFileSync(stub,`
import {DatabaseSync} from 'node:sqlite';
export const sqlite=new DatabaseSync(':memory:');export let user='owner',online=true;
export function signIn(v){user=v;}export function connect(v){online=v;}
export async function owner(){return user?{userId:user}:null;}
export const now=()=>Math.floor(Date.now()/1000),json=(d,s=200)=>Response.json(d,{status:s});
export const sameOrigin=r=>r.headers.get('origin')==='http://localhost:5173';
export async function expireJobs(){}export async function bridgeState(){return {examReady:online,critiqueReady:online,online};}
function statement(sql,args=[]){return {bind:(...a)=>statement(sql,a),first:async()=>sqlite.prepare(sql).get(...args)??null,all:async()=>({results:sqlite.prepare(sql).all(...args)}),run:async()=>({meta:sqlite.prepare(sql).run(...args)})};}
const db={prepare:statement,batch:async ss=>{sqlite.exec('BEGIN');try{const out=[];for(const s of ss)out.push(await s.run());sqlite.exec('COMMIT');return out;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};export const database=()=>db;
`);
function compile(file,replacements){let code=fs.readFileSync(file,'utf8');for(const [a,b]of Object.entries(replacements))code=code.replaceAll(a,b);const out=path.join(dir,file.replaceAll('/','-').replace('.ts','.mjs'));fs.writeFileSync(out,ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);return pathToFileURL(out).href;}
const serverUrl=pathToFileURL(stub).href;
const critic=compile('lib/review/critique-server.ts',{'../textbook/server':serverUrl,'../textbook/sources':url('lib/textbook/sources.ts'),'./critique':url('lib/review/critique.ts')});
const endpoint=await import(compile('app/api/textbook/cases/route.ts',{'../../../../lib/textbook/server':serverUrl,'../../../../lib/textbook/policy':url('lib/textbook/policy.ts'),'../../../../lib/textbook/sources':url('lib/textbook/sources.ts'),'../../../../lib/cases/model':url('lib/cases/model.ts'),'../../../../lib/review/critique-server':critic}));
const state=await import(serverUrl),db=state.sqlite;
for(const n of fs.readdirSync('drizzle').filter(n=>n.endsWith('.sql')).sort())db.exec(fs.readFileSync(path.join('drizzle',n),'utf8'));
async function post(body,origin='http://localhost:5173'){const r=await endpoint.POST(new Request('http://localhost:5173/api/textbook/cases',{method:'POST',headers:{'Content-Type':'application/json',Origin:origin},body:JSON.stringify(body)}));return {status:r.status,data:await r.json()};}
async function get(id){const r=await endpoint.GET(new Request('http://localhost:5173/api/textbook/cases'+(id?'?id='+id:'')));return {status:r.status,data:await r.json()};}
const draft={action:'create',requestId:crypto.randomUUID(),title:'架构复用',background:'同一公司，保留租户隔离与审计。\n结算规则不同。',questions:['复制代码有什么问题？','抽象策略接口的作用？']};
state.signIn(null);assert.equal((await post(draft)).status,403);state.signIn('owner');assert.equal((await post(draft,'https://evil.example')).status,403);
let r=await post(draft);assert.equal(r.status,201);const c=r.data.case,q=c.questions[0];
assert.equal((await post(draft)).data.case.id,c.id);assert.equal((await post({...draft,background:'另一个背景'})).status,409);
assert.equal(c.questions.length,2);assert.equal(c.questions[0].analysis,null);assert.equal(db.prepare('SELECT COUNT(*) AS n FROM textbook_jobs').get().n,0);
state.signIn('other');assert.equal((await get(c.id)).status,404);state.signIn('owner');
const attempt={action:'submit',caseId:c.id,questionId:q.id,requestId:crypto.randomUUID(),response:'保留结构，重新设计业务。 "引号"\nC:\\notes',references:[]};
state.connect(false);assert.equal((await post(attempt)).status,503);state.connect(true);
r=await post(attempt);assert.equal(r.status,202);assert.equal((await post(attempt)).status,202);assert.equal((await post({...attempt,response:'另一答案'})).status,409);
const job=db.prepare('SELECT * FROM textbook_jobs WHERE id=?').get(q.jobId);assert.equal(job.task_type,'case');assert.ok(job.question.includes(draft.background));assert.ok(job.question.includes(draft.questions[0]));assert.ok(!job.question.includes(draft.questions[1]));
assert.equal((await get(c.id)).data.case.questions[0].analysis,null);
const refs=[{rank:1,bookSha:'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9',chunkId:'a'.repeat(64),content:'架构复用应保留通用结构，适配业务差异。',pdfPages:[427],label:'教材412页（PDF427页）',chapter:'第12章'}];
db.prepare("UPDATE textbook_jobs SET status='done',answer=?,references_json=? WHERE id=?").run('参考分析[片段1]',JSON.stringify(refs),q.jobId);
r=await get(c.id);assert.equal(r.data.case.questions[0].analysis.answer,'参考分析[片段1]');assert.equal(r.data.case.questions[1].analysis,null);
assert.equal((await post({action:'advance',caseId:c.id,questionId:q.id,requestId:attempt.requestId})).status,202);
const critique=db.prepare('SELECT * FROM textbook_critiques WHERE id=?').get(attempt.requestId);assert.ok(critique.front.includes(draft.background));assert.equal(critique.back,'参考分析[片段1]');assert.equal(critique.response,attempt.response);assert.equal(critique.references_json,JSON.stringify(refs));
assert.equal((await post({action:'advance',caseId:c.id,questionId:q.id,requestId:attempt.requestId})).status,202);assert.equal(db.prepare('SELECT COUNT(*) AS n FROM textbook_critiques').get().n,1);
const result={summary:'遗漏差异适配',correct:[{point:'保留结构',ranks:[1]}],missing:[{point:'业务差异需要适配',ranks:[1]}],corrections:[],suggestion:'补充业务差异',insufficientEvidence:false};
db.prepare("UPDATE textbook_critiques SET status='done',result_json=? WHERE id=?").run(JSON.stringify(result),attempt.requestId);
const second={...attempt,requestId:crypto.randomUUID(),response:'保留结构并适配结算业务差异。'};assert.equal((await post(second)).status,202);
r=await get(c.id);assert.equal(r.data.case.questions[0].attempts.length,2);assert.equal(r.data.case.questions[0].attempts[0].response,attempt.response);assert.deepEqual(r.data.case.questions[0].attempts[0].critique.result.missing[0].ranks,[1]);assert.equal(db.prepare('SELECT COUNT(*) AS n FROM textbook_jobs').get().n,1);
console.log(JSON.stringify({passed:true,checks:['owner','origin','hidden_before_submit','shared_background','current_subquestion','idempotency','trusted_evidence','analysis_reuse','immutable_revisions','blue_citation_ranks']}));
