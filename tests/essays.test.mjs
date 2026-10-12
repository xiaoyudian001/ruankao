import test from 'node:test';import assert from 'node:assert/strict';
import {essayInput,essayTask,restoreEssayDraft,SECTIONS} from '../lib/essays/model.ts';
const raw={title:'订单项目',topic:'论软件架构设计',requirements:'结合实际项目',projectFacts:'本人负责 "架构"\n订单系统；没有量化效果。',drafts:{background:'背景草稿'}};
test('论文材料与段落草稿保持原文，不填造缺失事实',()=>{
 const v=essayInput(raw);assert.equal(v.projectFacts,raw.projectFacts);assert.equal(v.drafts.background,'背景草稿');assert.equal(v.drafts.design,'');
 const t=essayTask(v,2,'feedback','background');assert.equal(t.draft,'背景草稿');assert.equal(t.version,2);assert.equal(t.kind,'feedback');
});
test('恢复不完整浏览器草稿时每个段落仍是字符串',()=>{
 const v=restoreEssayDraft({drafts:{design:'保持原稿',abstract:99},projectFacts:27});assert.equal(v.drafts.design,'保持原稿');assert.equal(v.drafts.abstract,'');assert.equal(v.drafts.conclusion,'');assert.equal(v.projectFacts,'');
});
test('提纲不包含未选择段落草稿，拒绝未知段落及超长输入',()=>{
 const v=essayInput(raw);assert.equal(essayTask(v,0,'outline').draft,'');assert.equal(Object.keys(SECTIONS).length,5);
 assert.throws(()=>essayTask(v,0,'feedback','unknown'));assert.throws(()=>essayInput({...raw,projectFacts:''}));assert.throws(()=>essayInput({...raw,drafts:{background:'x'.repeat(8001)}}));
});
