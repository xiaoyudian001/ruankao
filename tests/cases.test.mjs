import test from 'node:test';
import assert from 'node:assert/strict';
import {caseInput,casePrompt} from '../lib/cases/model.ts';
test('共享背景和当前小问同时传递，保持引号和换行',()=>{
 const v=caseInput({title:'复用',background:'业务 "A"\n不同结算',questions:['如何复用？','策略接口有什么作用？']});
 const p=casePrompt(v.background,v.questions[1]);assert.ok(p.includes('业务 "A"\n不同结算'));assert.ok(p.includes('策略接口'));assert.ok(!p.includes('如何复用？'));
});
test('拒绝空背景、空小问、过多小问，保留编号含义',()=>{
 for(const v of [{background:'',questions:['问']},{background:'背景',questions:[]},{background:'背景',questions:Array(9).fill('问')},{background:'背景',questions:['']}])assert.throws(()=>caseInput(v));
 assert.equal(caseInput({background:'背景',questions:['①与②比较'],title:''}).questions[0],'①与②比较');
});
