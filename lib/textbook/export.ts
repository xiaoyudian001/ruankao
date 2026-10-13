import {sourceSummaries} from './sources.ts';
import {parseManifest} from './screenshots.ts';
import {cleanAnswer} from './policy.ts';
export type ExportJob={id:string;question:string;status:string;answer:string|null;error?:string|null;created_at:number;retrieval_mode:string;task_type:string;answer_action?:string;source_job_id?:string|null;references_json:string|null;screenshot_json:string|null;partial_answer?:string|null};
export function exportMarkdown(title:string,rows:ExportJob[],origin:string):string{
 const lines=['# '+title,'','导出自教材问答。教材出处来自各次回答的检索记录；原网页及截图链接需登录原网站。',''];
 const positions=new Map(rows.map((row,i)=>[row.id,i+1]));
 for(const [index,row]of rows.entries()){
  lines.push('## 第'+(index+1)+'条问题','',row.question,'');
  const action=row.answer_action==='edit'?'编辑后提问':row.answer_action==='regenerate'?'重新生成':'首次提问';
  const parent=row.source_job_id?positions.get(row.source_job_id):null;
  lines.push(`- 操作：${action}${parent?`，基于第${parent}条`:row.source_job_id?'，基于此前保存的问题':''}`);
  lines.push('- 模式：'+(row.retrieval_mode==='complete'?'完整检索实验':'当前问答')+'；题型：'+(row.task_type==='exam'?'真题解析':'教材问答'));
  lines.push('- 时间：'+new Date(row.created_at*1000).toISOString(),'');
  lines.push('### 回答','',row.status==='done'?cleanAnswer(row.answer??''):row.status==='cancelled'?'已停止，以下正文未完成、未通过最终校验：':row.status==='failed'?'本次回答失败：'+(row.error??'请在原网页重试。'):'等待处理，导出时尚未完成。','');
  if(row.status!=='done'&&row.partial_answer)lines.push('未完成正文（不可作为已核对教材答案）：','',cleanAnswer(row.partial_answer),'');
  const references=row.status==='done'?sourceSummaries(row.references_json):[];
  if(references.length){lines.push('### 教材出处','');for(const ref of references)lines.push(`- [片段${ref.rank}] ${ref.label}；${ref.chapter}；PDF 第${ref.pdfPages.join('、')}页。`);lines.push('');}
  try{if(row.screenshot_json){const manifest=parseManifest(row.screenshot_json);lines.push('### 原题截图','');manifest.images.forEach((_,i)=>lines.push(`[截图${i+1}](${origin}/api/textbook/screenshots?id=${encodeURIComponent(manifest.recognitionId)}&image=${i})`));lines.push('');}}catch{/* Corrupt attachments must not hide a usable saved answer. */}
  lines.push('---','');
 }
 return lines.join('\n')+'\n';
}
