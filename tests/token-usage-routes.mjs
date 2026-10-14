import './exam-routes.mjs';
import assert from 'node:assert/strict';import path from 'node:path';import {pathToFileURL} from 'node:url';
const dir=path.resolve('outputs/exam-route-test'),get=f=>import(pathToFileURL(path.join(dir,f)).href),state=await get('server.mjs'),chat=await get('app-api-textbook-chat-route.mjs'),bridge=await get('app-api-textbook-bridge-route.mjs'),db=state.sqlite;
const usage={scope:'answer_generation',inputTokens:4800,outputTokens:506,totalTokens:5306,reportedCalls:2,unreportedCalls:0,models:['MiniMax-M3']};
const post=async body=>{const r=await bridge.POST(new Request('http://localhost:5173/api/textbook/bridge',{method:'POST',headers:{Authorization:'Bearer local-test','Content-Type':'application/json'},body:JSON.stringify(body)}));return r.status;};
function add(){const id=crypto.randomUUID(),session=crypto.randomUUID(),lease=crypto.randomUUID();db.prepare('INSERT INTO textbook_sessions VALUES(?,?,?,?,?)').run(session,'owner','Token test',state.now(),state.now());db.prepare('INSERT INTO textbook_jobs(id,session_id,owner_id,question,status,created_at,leased_at,lease) VALUES(?,?,?,?,?,?,?,?)').run(id,session,'owner','解释概念','running',state.now(),state.now(),lease);return {id,session,lease};}
const a=add(),body={action:'complete',id:a.id,lease:a.lease,answer:'答案',references:[],tokenUsage:usage};
assert.equal(await post({...body,tokenUsage:{...usage,inputTokens:-1}}),400);
assert.equal(await post({...body,lease:crypto.randomUUID()}),409);
assert.equal(await post(body),200);
let r=await chat.GET(new Request('http://localhost:5173/api/textbook/chat?sessionId='+a.session));assert.deepEqual((await r.json()).messages[0].tokenUsage,usage);
assert.equal(await post(body),409);
const b=add();assert.equal(await post({...body,id:b.id,lease:b.lease,tokenUsage:null}),200);
assert.equal(db.prepare('SELECT token_usage_json FROM textbook_jobs WHERE id=?').get(b.id).token_usage_json,null);
const c=add();db.prepare('UPDATE textbook_jobs SET cancel_requested=1 WHERE id=?').run(c.id);assert.equal(await post({...body,id:c.id,lease:c.lease}),200);
assert.equal(db.prepare('SELECT token_usage_json FROM textbook_jobs WHERE id=?').get(c.id).token_usage_json,null);
console.log('Token usage persistence, legacy, invalid, lease and cancel checks passed');
