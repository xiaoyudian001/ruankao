import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {pathToFileURL} from 'node:url';
const file='lib/textbook/drafts.ts',api=fs.existsSync(file)?await import(pathToFileURL(process.cwd()+'/'+file).href):{};
const sid='11111111-1111-4111-8111-111111111111',image='22222222-2222-4222-8222-222222222222';
const memory=()=>{const data=new Map();return {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};};
const value={text:'我的问题\n"含转义\\字符"',mode:'complete',taskType:'exam',screenshot:{id:image,confirmed:false}};
test('draft reload retains settings and recognized attachment and isolates owner/session',()=>{
 assert.equal(typeof api.saveDraft,'function','缺少自动保存草稿');const s=memory();assert.equal(api.saveDraft(s,'one',sid,value,100),true);
 assert.deepEqual(api.loadDraft(s,'one',sid,101),value);assert.equal(api.loadDraft(s,'two',sid,101),null);assert.equal(api.loadDraft(s,'one',null,101),null);
 api.saveDraft(s,'one',null,{...value,text:'新会话'},100);assert.equal(api.loadDraft(s,'one',null,101).text,'新会话');
});
test('settings can be retained without text; unfinished uploads are not serialized',()=>{
 assert.equal(typeof api.saveDraft,'function');const s=memory();api.saveDraft(s,'one',sid,{...value,text:'',screenshot:{id:null,confirmed:false}},100);
 assert.deepEqual(api.loadDraft(s,'one',sid,101),{...value,text:'',screenshot:null});
});
test('success clears only the submitted draft; later edits survive',()=>{
 assert.equal(typeof api.clearSubmittedDraft,'function');const s=memory();api.saveDraft(s,'one',sid,value,100);
 assert.equal(api.clearSubmittedDraft(s,'one',sid,{...value,text:'different'}),false);assert.equal(api.loadDraft(s,'one',sid,101).text,value.text);
 assert.equal(api.clearSubmittedDraft(s,'one',sid,value),true);assert.equal(api.loadDraft(s,'one',sid,101),null);
});
test('expiry, corrupt records and unavailable storage are safe and observable',()=>{
 assert.equal(typeof api.loadDraft,'function');const s=memory();api.saveDraft(s,'one',sid,value,100);assert.equal(api.loadDraft(s,'one',sid,100+31*86400000),null);
 assert.equal(api.loadDraft({...s,getItem:()=>'{broken'},'one',sid,101),null);
 const blocked={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')},removeItem(){throw Error('blocked')}};
 assert.equal(api.saveDraft(blocked,'one',sid,value),false);assert.equal(api.loadDraft(blocked,'one',sid),null);assert.equal(api.removeDraft(blocked,'one',sid),false);
});
test('workspace restores each conversation and success switches from new draft without losing another draft',()=>{
 assert.equal(typeof api.DraftWorkspace,'function','缺少页面草稿状态管理');const s=memory(),work=new api.DraftWorkspace(s,'one');
 work.open(null);work.update(value);work.open(sid);assert.equal(work.value.text,'');work.update({...value,text:'旧会话草稿'});
 work.open(null);assert.equal(work.value.text,value.text);work.complete(null,sid,value);
 assert.equal(work.sessionId,sid);assert.equal(work.value.text,'旧会话草稿');assert.equal(api.loadDraft(s,'one',null),null);
 work.clear();assert.equal(work.value.text,'');assert.equal(api.loadDraft(s,'one',sid),null);
});
test('successful submission preserves a later in-memory edit when browser storage is blocked',()=>{
 assert.equal(typeof api.DraftWorkspace,'function');const blocked={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')},removeItem(){throw Error('blocked')}};
 const work=new api.DraftWorkspace(blocked,'one');work.open(sid);work.update(value);work.update({text:'后续问题'});work.complete(sid,sid,value);assert.equal(work.value.text,'后续问题');
});
test('draft settings reject arrays masquerading as enum strings',()=>{
 const storage=memory();assert.equal(api.saveDraft(storage,'one',sid,{...value,mode:['complete']}),false);assert.equal(api.saveDraft(storage,'one',sid,{...value,taskType:['exam']}),false);
});
