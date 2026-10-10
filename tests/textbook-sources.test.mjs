import test from 'node:test';
import assert from 'node:assert/strict';
import {BOOK_SHA,references,sourceSummaries,selectedReference} from '../lib/textbook/sources.ts';
const ref={rank:2,bookSha:BOOK_SHA,chunkId:'a'.repeat(64),content:'真实检索文本',pdfPages:[323,324],label:'教材第308～309页（PDF第323～324页）',chapter:'第9章'};
test('snapshot keeps original rank and summary does not leak full passage',()=>{
  assert.equal(references([ref])[0].rank,2);
  assert.equal(sourceSummaries(JSON.stringify([ref]))[0].content,undefined);
  assert.equal(selectedReference(JSON.stringify([ref]),2,324).content,ref.content);
});
test('page requests stay within the selected actual retrieved source',()=>{
  assert.equal(selectedReference([ref],2,325),null);
  assert.equal(selectedReference([ref],1,323),null);
  assert.equal(selectedReference([ref],'2',323),null);
  assert.equal(selectedReference('not-json',2,323),null);
});
test('reject forged books, duplicate ranks, and broad or invalid pages',()=>{
  for(const invalid of [[{...ref,bookSha:'other'}],[ref,ref],[{...ref,pdfPages:[323,325]}],[{...ref,pdfPages:[0]}],[{...ref,content:'x'.repeat(12001)}]])assert.throws(()=>references(invalid));
});
