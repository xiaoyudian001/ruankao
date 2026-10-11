import test from 'node:test';
import assert from 'node:assert/strict';
import {references,sourceSummaries,BOOK_SHA} from '../lib/textbook/sources.ts';
const figure={id:'b'.repeat(64),caption:'图12-2 三层C/S与B/S架构',pdfPage:427,bbox:[.1,.2,.8,.3],pageSize:[500,700]};
const ref={rank:6,bookSha:BOOK_SHA,chunkId:'a'.repeat(64),content:'原书图题和同页正文',pdfPages:[427],label:'教材第412页（PDF第427页）',chapter:'第12章',figures:[figure]};
test('figure summary retains crop identity without local paths',()=>{
 assert.deepEqual(sourceSummaries([ref])[0].figures,[figure]);
 assert.equal(sourceSummaries([ref])[0].content,undefined);
});
test('reject figures outside source page and invalid crop bounds',()=>{
 for(const wrong of [{...figure,pdfPage:428},{...figure,bbox:[.9,.2,.8,.3]},{...figure,bbox:[0,0,0,1]},{...figure,id:'local/path.png'},{...figure,pageSize:[0,700]}])assert.throws(()=>references([{...ref,figures:[wrong]}]));
 assert.throws(()=>references([{...ref,figures:[figure,figure]}]));
});

test('table and formula source kinds survive validated summaries',()=>{
 for(const kind of ['table','formula','figure']){
  const item={...figure,kind};assert.equal(sourceSummaries([{...ref,figures:[item]}])[0].figures[0].kind,kind);
 }
});

test('reject unrecognized visual source kind',()=>{
 assert.throws(()=>references([{...ref,figures:[{...figure,kind:'external-image'}]}]));
});
