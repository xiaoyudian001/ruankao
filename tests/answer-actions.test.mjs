import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {pathToFileURL} from 'node:url';
import {saveRecovery,loadRecovery} from '../lib/textbook/chat-recovery.ts';import {saveDraft,loadDraft,clearSubmittedDraft,DraftWorkspace} from '../lib/textbook/drafts.ts';
import * as actions from '../lib/textbook/answer-actions.ts';
const file='lib/textbook/export.ts',api=fs.existsSync(file)?await import(pathToFileURL(process.cwd()+'/'+file).href):{};
const id='11111111-1111-4111-8111-111111111111',source='22222222-2222-4222-8222-222222222222';
const memory=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)};};

test('recovering an uncertain regeneration preserves an independent draft even after rejection',()=>{
 const s=memory(),ordinary={text:'尚未发送的新问题',mode:'complete',taskType:'qa',screenshot:null},submitted={...ordinary,text:'历史问题',retrySource:{id:source,action:'regenerate'}};
 saveDraft(s,'owner',id,ordinary);const work=new DraftWorkspace(s,'owner');work.open(id,submitted,true);
 assert.deepEqual(work.value,ordinary);work.update({retrySource:undefined});assert.deepEqual(loadDraft(s,'owner',id),ordinary);
 const empty=new DraftWorkspace(memory(),'owner');empty.open(id,submitted,true);assert.deepEqual(empty.value,submitted);
});
test('uncertain edit preserves source and action over reload',()=>{const s=memory(),r={id,sessionId:id,question:'改好的问题',mode:'complete',taskType:'qa',screenshotId:null,answerAction:'edit',sourceJobId:source};saveRecovery(s,'owner',{sessionId:id,request:r});assert.deepEqual(loadRecovery(s,'owner').request,r);});
test('edit association survives draft reload; regenerating same text never clears an ordinary draft',()=>{const s=memory(),d={text:'same question',mode:'complete',taskType:'qa',screenshot:null,retrySource:{id:source,action:'edit'}};saveDraft(s,'owner',id,d);assert.deepEqual(loadDraft(s,'owner',id),d);const ordinary={...d,retrySource:undefined};saveDraft(s,'owner',id,ordinary);assert.equal(clearSubmittedDraft(s,'owner',id,{...d,retrySource:{id:source,action:'regenerate'}}),false);});
test('Markdown contains lineage, actual page labels, pending status and private screenshot links',()=>{
 assert.equal(typeof api.exportMarkdown,'function','缺少会话导出');const text=api.exportMarkdown('我的学习记录',[{id:source,question:'原问题',status:'done',answer:'解释[片段1]',created_at:100,retrieval_mode:'complete',task_type:'qa',answer_action:'original',source_job_id:null,references_json:'[]',screenshot_json:null},{id,question:'修改问题',status:'queued',answer:null,created_at:200,retrieval_mode:'complete',task_type:'qa',answer_action:'edit',source_job_id:source,references_json:'[]',screenshot_json:null}], 'https://example.test');
 assert.ok(text.includes('编辑后提问'));assert.ok(text.includes('第1条'));assert.ok(text.includes('等待处理'));assert.ok(!text.includes('undefined'));assert.ok(!text.includes('history_json'));
});
test('reopening an edit asks before overwriting a revised draft, including the same source',()=>{
 assert.equal(typeof actions.shouldConfirmEdit,'function');const target={id:source,question:'原题',retrieval_mode:'complete',task_type:'qa',screenshotId:null};
 assert.equal(actions.shouldConfirmEdit({text:'已经修改好的题目',mode:'complete',taskType:'qa',screenshot:null,retrySource:{id:source,action:'edit'}},target),true);
 assert.equal(actions.shouldConfirmEdit({text:'原题',mode:'complete',taskType:'qa',screenshot:null,retrySource:{id:source,action:'edit'}},target),false);
});
test('export preserves only validated source page metadata and removes model think blocks',()=>{
 const refs=[{rank:1,bookSha:'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9',chunkId:'a'.repeat(64),content:'自写验证文本',pdfPages:[22],label:'教材第7页（PDF第22页）',chapter:'样例章'}];
 const text=api.exportMarkdown('验证记录',[{id,question:'问题',status:'done',answer:'<think>不应导出的区域</think>正文[片段1]',created_at:100,retrieval_mode:'default',task_type:'qa',references_json:JSON.stringify(refs),screenshot_json:null}], 'https://example.test');assert.ok(text.includes('教材第7页（PDF第22页）'));assert.ok(text.includes('样例章'));assert.ok(!text.includes('不应导出的区域'));assert.ok(!text.includes('自写验证文本'));
});
