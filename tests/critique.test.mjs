import test from 'node:test';
import assert from 'node:assert/strict';
test('critique accepts evidence within original reference ranks',async()=>{
 const {validateCritique}=await import('../lib/review/critique.ts');
 const result=validateCritique({summary:'已理解定义',correct:[{point:'答对平均时间',ranks:[2]}],missing:[],corrections:[],suggestion:'复述定义',insufficientEvidence:false},[2]);
 assert.equal(result.correct[0].ranks[0],2);
});
test('critique rejects fabricated references and unsupported points',async()=>{
 const {validateCritique}=await import('../lib/review/critique.ts');
 const sample={summary:'摘要',correct:[{point:'要点',ranks:[9]}],missing:[],corrections:[],suggestion:'建议',insufficientEvidence:false};
 assert.throws(()=>validateCritique(sample,[2]));
 assert.throws(()=>validateCritique({...sample,correct:[{point:'要点',ranks:[]}]},[2]));
});
test('insufficient evidence is explicit and malicious payloads are not rendered',async()=>{
 const {validateCritique}=await import('../lib/review/critique.ts');
 const sample={summary:'原文未覆盖',correct:[],missing:[],corrections:[],suggestion:'核对原文',insufficientEvidence:true};
 assert.equal(validateCritique(sample,[1]).insufficientEvidence,true);
 assert.throws(()=>validateCritique({...sample,summary:'<think>private</think>'},[1]));
 assert.throws(()=>validateCritique({...sample,insufficientEvidence:'yes'},[1]));
});
