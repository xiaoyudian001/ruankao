import test from 'node:test';
import assert from 'node:assert/strict';
import { historySnapshot, rewriteDiagnostic } from '../lib/textbook/conversation.ts';

test('history is bounded, chronological, and contains completed content only',()=>{
  const rows=[{question:'q4',answer:'a'.repeat(2000)},{question:'q3',answer:'a3'},{question:'q2',answer:'a2'},{question:'q1',answer:'a1'}];
  const h=JSON.parse(historySnapshot(rows));
  assert.deepEqual(h.map(r=>r.question),['q2','q3','q4']);
  assert.equal(h[2].answer.length,1000);
  assert.equal(historySnapshot([]),'[]');
});
test('rewrite diagnostics reject invalid routes and preserve only plain bounded search text',()=>{
  assert.deepEqual(rewriteDiagnostic({retrievalQuery:' MTBF是什么？ ',rewriteRoute:'rewritten'}),{query:'MTBF是什么？',route:'rewritten'});
  assert.throws(()=>rewriteDiagnostic({retrievalQuery:'MTBF',rewriteRoute:'evil'}));
  assert.throws(()=>rewriteDiagnostic({retrievalQuery:'x'.repeat(2001),rewriteRoute:'direct'}));
  assert.deepEqual(rewriteDiagnostic({}),{query:null,route:null});
});
test('internal case diagnostics retain the full shared context with a bounded explicit limit',()=>{
 const value={retrievalQuery:'背景'.repeat(1800)+'当前小问',rewriteRoute:'direct'};
 assert.equal(rewriteDiagnostic(value,6000).query,value.retrievalQuery);
 assert.throws(()=>rewriteDiagnostic(value));
 assert.throws(()=>rewriteDiagnostic({...value,retrievalQuery:'x'.repeat(6001)},6000));
});
