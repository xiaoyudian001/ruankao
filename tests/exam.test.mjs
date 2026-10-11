import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePractice,practiceView,validTaskType,sameTaskRequest} from '../lib/textbook/exam.ts';
const value={question:'可用性如何计算？',options:[{label:'A',text:'MTBF/(MTBF+MTTR)'},{label:'B',text:'MTTR/MTBF'},{label:'C',text:'MTBF+MTTR'},{label:'D',text:'MTBF-MTTR'}],correct:'A',explanation:'计算可用性采用A式。[片段1]',ranks:[1]};
test('practice answer is hidden until a valid option is submitted',()=>{
 const p=validatePractice(value,[1]);
 assert.deepEqual(Object.keys(practiceView(p,null)).sort(),['options','question']);
 assert.equal(JSON.stringify(practiceView(p,null)).includes('correct'),false);
 assert.equal(practiceView(p,'B').isCorrect,false);assert.equal(practiceView(p,'A').isCorrect,true);
 assert.equal(practiceView(p,'B').correct,'A');assert.equal(practiceView(null,null),null);
});
test('reject unknown sources, invalid answers, duplicate options and unsafe text',()=>{
 assert.throws(()=>validatePractice({...value,ranks:[9]},[1]));
 assert.throws(()=>validatePractice({...value,explanation:'编造[片段9]'},[1]));
 assert.throws(()=>validatePractice({...value,correct:'Z'},[1]));
 assert.throws(()=>validatePractice({...value,options:[value.options[0],value.options[0],...value.options.slice(2)]},[1]));
 assert.throws(()=>validatePractice({...value,question:'<think>推理'},[1]));
 assert.throws(()=>practiceView(value,'Z'));
 assert.throws(()=>validatePractice(value,[]));
});
test('question task type is a separate idempotency dimension',()=>{
 assert.equal(validTaskType(undefined),'qa');assert.equal(validTaskType('exam'),'exam');assert.throws(()=>validTaskType('agent'));
 assert.equal(sameTaskRequest('exam','exam'),true);assert.equal(sameTaskRequest('qa','exam'),false);
});
