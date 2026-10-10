import test from 'node:test';
import assert from 'node:assert/strict';
import { studyDate, addDays, scheduleReview, cardText, planDays } from '../lib/review/model.ts';

test('Shanghai natural day crosses UTC midnight without using browser timezone',()=>{
  assert.equal(studyDate(new Date('2026-10-10T16:01:00Z')),'2026-10-11');
  assert.equal(addDays('2026-12-31',1),'2027-01-01');
  assert.throws(()=>addDays('2026-02-30',1));
});
test('remembered cards progress 1,3,7,14 days; forgotten and partial reset',()=>{
  assert.deepEqual(scheduleReview(0,'remembered','2026-10-10'),{streak:1,interval:1,dueDate:'2026-10-11'});
  assert.deepEqual(scheduleReview(1,'remembered','2026-10-10'),{streak:2,interval:3,dueDate:'2026-10-13'});
  assert.equal(scheduleReview(2,'remembered','2026-10-10').interval,7);
  assert.equal(scheduleReview(4,'remembered','2026-10-10').interval,14);
  for(const grade of ['forgotten','partial'])assert.deepEqual(scheduleReview(3,grade,'2026-10-10'),{streak:0,interval:1,dueDate:'2026-10-11'});
  assert.throws(()=>scheduleReview(1,'wrong','2026-10-10'));
});
test('cards accept multiline mixed language without discarding whitespace and reject blank or oversize',()=>{
  assert.equal(cardText(' System Architecture\n是什么？ ',2000),'System Architecture\n是什么？');
  assert.throws(()=>cardText(' ',2000));assert.throws(()=>cardText('x'.repeat(2001),2000));
});
test('40-day plan preserves original dates and remains usable after last day',()=>{
  const days=planDays();assert.equal(days.length,40);assert.equal(days[0],'2026-09-15');assert.equal(days[39],'2026-10-24');
  assert.equal(scheduleReview(3,'remembered',days[39]).dueDate,'2026-11-07');
});
