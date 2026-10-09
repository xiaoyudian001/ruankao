import test from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../lib/textbook/policy.ts';

test('retrieval modes are whitelisted, historical requests default safely',()=>{
  assert.equal(p.validRetrievalMode(undefined),'default');
  assert.equal(p.validRetrievalMode(null),'default');
  assert.equal(p.validRetrievalMode('complete'),'complete');
  for(const value of ['other','http://evil',{},''])assert.throws(()=>p.validRetrievalMode(value));
});
test('only live advertised modes may be submitted',()=>{
  assert.deepEqual(p.availableRetrievalModes(null,100),[]);
  assert.deepEqual(p.availableRetrievalModes({last_seen:100,ready:1,modes:'["default","complete","other"]'},110),['default','complete']);
  assert.deepEqual(p.availableRetrievalModes({last_seen:100,ready:1,modes:'["default","complete"]'},146),[]);
  assert.deepEqual(p.availableRetrievalModes({last_seen:100,ready:1,modes:'bad'},110),['default']);
});
test('idempotent request reuse cannot change retrieval mode or question',()=>{
  const prior={question:'test',retrieval_mode:'default',session_id:'s'};
  assert.equal(p.sameJobRequest(prior,'test','default',null),true);
  assert.equal(p.sameJobRequest(prior,'test','complete',null),false);
  assert.equal(p.sameJobRequest(prior,'changed','default',null),false);
  assert.equal(p.sameJobRequest(prior,'test','default','other'),false);
});
