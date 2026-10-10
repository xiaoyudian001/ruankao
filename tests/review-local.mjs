// Run only against the existing Sites local sign-in preview, never the live Site.
import assert from 'node:assert/strict';
const origin='http://localhost:5173';
const headers={'Cookie':'__sites_local_auth=1','Origin':origin,'Content-Type':'application/json'};
async function call(body,extra={}){
  const r=await fetch(origin+'/api/textbook/review',{method:'POST',headers:{...headers,...extra},body:JSON.stringify(body)});
  const text=await r.text();let data;try{data=JSON.parse(text);}catch{data={error:text};}return {status:r.status,data};
}
const jobId='10000000-0000-4000-8000-000000000002';
let r=await call({action:'favorite',jobId,answer:'forged browser content'});assert.equal(r.status,200);
let data=await (await fetch(origin+'/api/textbook/review',{headers})).json();
const favorite=data.favorites.find(f=>f.job_id===jobId);assert.ok(favorite);assert.notEqual(favorite.answer,'forged browser content');
assert.equal(data.favorites.filter(f=>f.job_id===jobId).length,1);
const sample='MTBF 与 "System Architecture"\n路径 C:\\教材\\notes';
const prior=data.cards.find(c=>c.favorite_id===favorite.id);
r=await call({action:'card',favoriteId:favorite.id,front:prior?.front??'MTBF是什么？',back:prior?.back??favorite.answer});assert.equal(r.status,200);
assert.equal((await call({action:'card',favoriteId:favorite.id,front:'不同的并发编辑',back:favorite.answer})).status,409);
data=await (await fetch(origin+'/api/textbook/review',{headers})).json();const card=data.cards.find(c=>c.favorite_id===favorite.id);
assert.equal(data.cards.filter(c=>c.favorite_id===favorite.id).length,1);
const requestId=crypto.randomUUID(),body={action:'review',cardId:card.id,version:card.version,requestId,grade:'partial',response:sample};
r=await call(body);assert.equal(r.status,200);assert.equal(r.data.review.response,sample);
const retry=await call(body);assert.equal(retry.status,200);assert.equal(retry.data.review.id,r.data.review.id);
assert.equal((await call({...body,requestId:crypto.randomUUID()})).status,409);
assert.equal((await call({...body,response:'changed retry'})).status,409);
assert.equal((await call({action:'favorite',jobId},{Origin:'https://invalid.example'})).status,403);
assert.equal((await call({action:'favorite',jobId},{Cookie:''})).status,403);
assert.equal((await call({action:'card',favoriteId:favorite.id,front:' ',back:'answer'})).status,400);
data=await (await fetch(origin+'/api/textbook/review',{headers})).json();assert.equal(data.reviews.filter(e=>e.id===requestId).length,1);
assert.equal(data.cards.find(c=>c.id===card.id).streak,0);
console.log(JSON.stringify({passed:true,checks:['trusted_snapshot','favorite_and_card_idempotency','multiline_quote_backslash_roundtrip','review_retry','stale_version','request_reuse','origin','owner','blank_card','reset_schedule']}));
