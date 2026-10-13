import {database} from './server';
export const LIVE_CHAT = `owner_id=? AND NOT EXISTS (SELECT 1 FROM textbook_session_deletions d WHERE d.session_id=textbook_sessions.id)
 AND EXISTS (SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND j.task_type IN ('qa','exam'))`;
export const UNDELETED_SESSION = `SELECT id FROM textbook_sessions WHERE id=? AND owner_id=? AND NOT EXISTS (SELECT 1 FROM textbook_session_deletions d WHERE d.session_id=textbook_sessions.id)`;
export const DELETE_SESSION = `INSERT OR IGNORE INTO textbook_session_deletions(session_id,owner_id,deleted_at)
 SELECT id,owner_id,? FROM textbook_sessions WHERE id=? AND owner_id=?
 AND EXISTS (SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND j.task_type IN ('qa','exam'))
 AND NOT EXISTS (SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND (j.status IN ('queued','running') OR j.task_type NOT IN ('qa','exam')))`;
export function searchText(value:unknown):string{
 if(value==null)return '';if(typeof value!=='string'||value.length>100)throw Error('搜索词请保持在 100 字以内。');return value.trim();
}
export function sessionTitle(value:unknown):string{
 if(typeof value!=='string'||!value.trim()||value.trim().length>80||/[\r\n\x00-\x1f]/.test(value))throw Error('会话名称请输入 1～80 字，不能换行。');return value.trim();
}
export async function sessionPage(owner:string,query:string,cursor:string|null){
 let afterTime=0,afterId='';
 if(cursor){const match=/^(\d{1,12})\|([a-f0-9-]{36})$/i.exec(cursor);if(!match)throw Error('分页标识无效。');afterTime=Number(match[1]);afterId=match[2];}
 const rows=await database().prepare(`SELECT id,title,updated_at,
 EXISTS(SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND j.status IN ('queued','running')) AS pending
 FROM textbook_sessions WHERE ${LIVE_CHAT}
 AND (?='' OR instr(lower(title),lower(?))>0 OR EXISTS(SELECT 1 FROM textbook_jobs j WHERE j.session_id=textbook_sessions.id AND j.task_type IN ('qa','exam') AND (instr(lower(j.question),lower(?))>0 OR instr(lower(COALESCE(j.answer,'')),lower(?))>0)))
 AND (?='' OR updated_at<? OR (updated_at=? AND id<?))
 ORDER BY updated_at DESC,id DESC LIMIT 51`).bind(owner,query,query,query,query,afterId,afterTime,afterTime,afterId).all<{id:string;title:string;updated_at:number;pending:number}>();
 const sessions=rows.results.slice(0,50).map(r=>({...r,pending:r.pending===1})),last=sessions.at(-1);
 return {sessions,nextCursor:rows.results.length>50&&last?last.updated_at+'|'+last.id:null};
}
