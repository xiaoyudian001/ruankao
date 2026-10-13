export function progressSnapshot(body:Record<string,unknown>):{seq:number;text:string}{
 if(!Number.isSafeInteger(body.seq)||Number(body.seq)<1||Number(body.seq)>10000||typeof body.text!=='string'||body.text.length>60000||/[<>]/.test(body.text))throw new Error('Invalid progress');
 return {seq:Number(body.seq),text:body.text};
}
export const PROGRESS_SQL=`UPDATE textbook_jobs SET partial_answer=?,partial_seq=?
WHERE id=? AND status='running' AND lease=? AND leased_at>=? AND cancel_requested=0 AND partial_seq<? AND task_type IN ('qa','exam') RETURNING id`;
export const STOPPED_SQL=`UPDATE textbook_jobs SET status='cancelled',answer=partial_answer,error=NULL,completed_at=?,lease=NULL,references_json='[]',exam_json=NULL
WHERE id=? AND status='running' AND lease=? AND leased_at>=? AND cancel_requested=1 AND task_type IN ('qa','exam') RETURNING id`;
