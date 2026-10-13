import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';

const source='lib/textbook/chat-recovery.ts';
const exists=fs.existsSync(source);
const api=exists?await import(pathToFileURL(process.cwd()+'/'+source).href):{};
const sid='11111111-1111-4111-8111-111111111111',rid='22222222-2222-4222-8222-222222222222';
const request={id:rid,sessionId:null,question:'解释 RTO 与 RPO',mode:'complete',taskType:'qa',screenshotId:null};
const memory=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)};};

test('reload retains active session and original uncertain request, isolated by owner',()=>{
 assert.equal(typeof api.saveRecovery,'function','缺少刷新恢复机制');
 const storage=memory();api.saveRecovery(storage,'one',{sessionId:sid,request},1000);
 assert.deepEqual(api.loadRecovery(storage,'one',1001),{sessionId:sid,request});
 assert.equal(api.loadRecovery(storage,'two',1001),null);
 assert.equal(api.loadRecovery(storage,'one',1000+86400001),null);
});
test('corrupt or unavailable storage cannot break the chat',()=>{
 assert.equal(typeof api.loadRecovery,'function');
 const s=memory();api.saveRecovery(s,'one',{sessionId:sid,request},1000);
 const bad={...s,getItem:()=>'{"sessionId":"malformed"}'};
 assert.equal(api.loadRecovery(bad,'one',1001),null);
 const blocked={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')},removeItem(){throw Error('blocked')}};
 assert.equal(api.loadRecovery(blocked,'one',1001),null);
 assert.doesNotThrow(()=>api.saveRecovery(blocked,'one',{sessionId:sid,request},1000));
});
test('polling prevents overlap and ignores an old session response',async()=>{
 assert.equal(typeof api.ChatReader,'function');
 const reader=new api.ChatReader(1000);let finish;
 const old=reader.read('old',()=>new Promise(resolve=>finish=resolve));
 assert.equal(await reader.read('old',()=>{throw Error('must not overlap')}),null);
 assert.deepEqual(await reader.read('new',async()=>({answer:'new'})),{answer:'new'});
 finish({answer:'old'});assert.equal(await old,null);
});
test('a hanging read times out and allows the next poll',async()=>{
 assert.equal(typeof api.ChatReader,'function');
 const reader=new api.ChatReader(15);
 await assert.rejects(reader.read('same',()=>new Promise(()=>{})),/读取超时/);
 assert.deepEqual(await reader.read('same',async()=>({ok:true})),{ok:true});
});
test('progress counts real queue and run times and does not invent retrieval stages',()=>{
 assert.equal(typeof api.taskProgress,'function');
 const queued=api.taskProgress({status:'queued',created_at:100,leased_at:null},170);
 assert.equal(queued.elapsed,70);assert.match(queued.label,/排队/);assert.equal(queued.slow,true);
 const running=api.taskProgress({status:'running',created_at:100,leased_at:150},175);
 assert.equal(running.elapsed,75);assert.equal(running.running,25);assert.match(running.label,/处理/);
 assert.equal(api.taskProgress({status:'running',created_at:999,leased_at:999},175).elapsed,0);
});
