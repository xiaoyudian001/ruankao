import {database,json,owner,sameOrigin} from '../../../../lib/textbook/server';
import {validId} from '../../../../lib/textbook/policy';
import {storedReferences} from '../../../../lib/textbook/sources';
import {savedPractice,practiceView} from '../../../../lib/textbook/exam';

export async function POST(request:Request){
 try{
  const user=await owner();if(!user)return json({error:'请使用网站所有者账号登录。'},403);
  if(!sameOrigin(request))return json({error:'请求来源无效。'},403);
  if(Number(request.headers.get('content-length')??0)>1000)return json({error:'提交过长。'},400);
  const body=await request.json() as Record<string,unknown>;
  if(!validId(body.jobId)||typeof body.choice!=='string'||!['A','B','C','D'].includes(body.choice))return json({error:'请选择一个有效选项。'},400);
  const db=database();
  const read=()=>db.prepare("SELECT exam_json,practice_choice,references_json FROM textbook_jobs WHERE id=? AND owner_id=? AND task_type='exam' AND status='done'").bind(body.jobId,user.userId).first<{exam_json:string|null;practice_choice:string|null;references_json:string}>();
  let row=await read();if(!row)return json({error:'练习不存在。'},404);
  const practice=savedPractice(row.exam_json,storedReferences(row.references_json).map(r=>r.rank));
  if(!practice)return json({error:'本次未生成类似练习。'},409);
  if(row.practice_choice==null){
   await db.prepare("UPDATE textbook_jobs SET practice_choice=? WHERE id=? AND owner_id=? AND task_type='exam' AND status='done' AND practice_choice IS NULL").bind(body.choice,body.jobId,user.userId).run();
   row=await read();
  }
  if(row?.practice_choice!==body.choice)return json({error:'本题已提交其他选项，答案已保存。请刷新查看结果。'},409);
  return json({practice:practiceView(practice,row.practice_choice)});
 }catch(error){console.error('exam submit',error instanceof Error?error.name:'error');return json({error:'练习提交暂时失败，请重试。'},503);}
}
