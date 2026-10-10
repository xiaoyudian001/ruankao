import {database,now} from '../textbook/server';
import {storedReferences} from '../textbook/sources';
import {validateCritique,type CritiqueJob} from './critique';

export async function expireCritiques(){
 await database().batch([
  database().prepare("UPDATE textbook_critiques SET status='failed',error=?,completed_at=?,lease=NULL WHERE status='queued' AND created_at<?").bind('点评未及时领取，请检查电脑连接后重试。',now(),now()-180),
  database().prepare("UPDATE textbook_critiques SET status='failed',error=?,completed_at=?,lease=NULL WHERE status='running' AND leased_at<?").bind('AI 点评超时。你仍可继续自评，或稍后重试。',now(),now()-180),
 ]);
}
export const CRITIQUE_CLAIM_SQL=`UPDATE textbook_critiques SET status='running',lease=?,leased_at=?
WHERE id=(SELECT id FROM textbook_critiques WHERE status='queued' ORDER BY created_at,rowid LIMIT 1)
AND status='queued' AND NOT EXISTS(SELECT 1 FROM textbook_critiques WHERE status='running')
AND NOT EXISTS(SELECT 1 FROM textbook_jobs WHERE status='running')
RETURNING id,lease,front,back,response,references_json`;
export const CRITIQUE_COMPLETE_SQL=`UPDATE textbook_critiques SET status=?,result_json=?,error=?,completed_at=?,lease=NULL
WHERE id=? AND status='running' AND lease=? AND leased_at>=? RETURNING id`;
export function critiqueSummary(row:Record<string,unknown>):CritiqueJob{
 let result=null;try{if(row.status==='done')result=validateCritique(JSON.parse(String(row.result_json)),storedReferences(row.references_json).map(r=>r.rank));}catch{return {id:String(row.id),status:'failed',result:null,error:'保存的点评无法校验，请继续自评。'};}
 return {id:String(row.id),status:row.status as CritiqueJob['status'],result,error:typeof row.error==='string'?row.error:null};
}
