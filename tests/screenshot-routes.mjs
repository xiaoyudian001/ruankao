// Extend the existing real-route SQLite/R2 adapter with screenshot lifecycle checks.
import './exam-routes.mjs';
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import ts from 'typescript';
const root=process.cwd(),dir=path.join(root,'outputs','exam-route-test'),url=f=>pathToFileURL(path.join(root,f)).href,serverUrl=pathToFileURL(path.join(dir,'server.mjs')).href;
const state=await import(serverUrl),chat=await import(pathToFileURL(path.join(dir,'app-api-textbook-chat-route.mjs')).href),bridge=await import(pathToFileURL(path.join(dir,'app-api-textbook-bridge-route.mjs')).href);
let code=fs.readFileSync('app/api/textbook/screenshots/route.ts','utf8');for(const [a,b] of Object.entries({'../../../../lib/textbook/server':serverUrl,'../../../../lib/textbook/policy':url('lib/textbook/policy.ts'),'../../../../lib/textbook/screenshots':url('lib/textbook/screenshots.ts')}))code=code.replaceAll(a,b);
const file=path.join(dir,'screenshots.mjs');fs.writeFileSync(file,ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);const shots=await import(pathToFileURL(file).href);
const jsonPost=async(route,body,headers={})=>{const r=await route.POST(new Request('http://localhost:5173/api/textbook/bridge',{method:'POST',headers:{'Content-Type':'application/json',Origin:'http://localhost:5173',...headers},body:JSON.stringify(body)}));return {status:r.status,data:await r.json()};};
const auth={Authorization:'Bearer local-test'},id=crypto.randomUUID();
const png=new Uint8Array(40);png.set([137,80,78,71,13,10,26,10]);new DataView(png.buffer).setUint32(8,13);png.set([73,72,68,82],12);new DataView(png.buffer).setUint32(16,600);new DataView(png.buffer).setUint32(20,800);
async function upload(uploadId=id,bytes=png,origin='http://localhost:5173',count=1){const form=new FormData();form.set('requestId',uploadId);for(let i=0;i<count;i++)form.append('images',new File([bytes],'题目.png',{type:'image/png'}));const r=await shots.POST(new Request('http://localhost:5173/api/textbook/screenshots',{method:'POST',headers:{Origin:origin},body:form}));return {status:r.status,data:await r.json()};}
state.signIn(null);assert.equal((await upload()).status,403);state.signIn('owner');assert.equal((await upload(id,png,'https://evil.example')).status,403);assert.equal((await upload(id,png,undefined,3)).status,400);assert.equal((await upload(id,new Uint8Array(50))).status,400);assert.equal((await upload()).status,503);
await jsonPost(bridge,{action:'heartbeat',ready:true,modes:['default','complete'],examReady:true,screenshotReady:true},auth);
assert.equal((await upload()).status,202);assert.equal((await upload()).status,200);const different=png.slice();different[39]=1;assert.equal((await upload(id,different)).status,409);assert.equal(state.objects.size,1);
const job=(await jsonPost(bridge,{action:'claim'},auth)).data.job;assert.equal(job.task_type,'recognize');assert.ok(job.screenshot_json);
assert.equal((await jsonPost(bridge,{action:'claim'},auth)).data.job,null);
assert.equal((await jsonPost(bridge,{action:'screenshotRead',id,lease:crypto.randomUUID()},auth)).status,409);
assert.equal((await jsonPost(bridge,{action:'screenshotRead',id,lease:job.lease},auth)).data.images.length,1);
assert.equal((await jsonPost(bridge,{action:'recognitionComplete',id,lease:job.lease,recognition:{question:'',notes:''}},auth)).status,400);
assert.equal((await jsonPost(bridge,{action:'recognitionComplete',id,lease:job.lease,recognition:{question:'系统架构师职责？\nA.评估需求\nB.采购',notes:'核对B'}},auth)).status,200);
assert.equal((await jsonPost(bridge,{action:'screenshotRead',id,lease:job.lease},auth)).status,409);
const read=()=>shots.GET(new Request('http://localhost:5173/api/textbook/screenshots?id='+id));state.signIn('other');assert.equal((await read()).status,404);assert.equal((await jsonPost(chat,{requestId:crypto.randomUUID(),question:'核对后题目',taskType:'exam',screenshotId:id})).status,400);state.signIn('owner');
assert.equal((await (await read()).json()).recognition.notes,'核对B');assert.equal((await shots.GET(new Request('http://localhost:5173/api/textbook/screenshots?id='+id+'&image=0'))).headers.get('Cache-Control'),'private, no-store');
const hidden=await (await chat.GET(new Request('http://localhost:5173/api/textbook/chat?sessionId='+job.session_id))).json();assert.equal(hidden.messages.length,0);assert.ok(!hidden.sessions.some(s=>s.id===job.session_id));
const examRequest={requestId:crypto.randomUUID(),question:'用户核对后的题目：A.评估需求 B.采购',taskType:'exam',screenshotId:id};assert.equal((await jsonPost(chat,examRequest)).status,202);assert.equal((await jsonPost(chat,{...examRequest,screenshotId:null})).status,409);
const examJob=(await jsonPost(bridge,{action:'claim'},auth)).data.job;assert.equal(examJob.question,examRequest.question);assert.deepEqual(JSON.parse(examJob.screenshot_json),JSON.parse(job.screenshot_json));assert.equal((await jsonPost(bridge,{action:'screenshotRead',id:examJob.id,lease:examJob.lease},auth)).data.images.length,1);
console.log(JSON.stringify({passed:true,screenshots:['private_upload','file_validation','idempotency','same_queue','active_lease','recognized_text','hidden_internal_history','owner_image_read','corrected_text_with_original_image']}));
