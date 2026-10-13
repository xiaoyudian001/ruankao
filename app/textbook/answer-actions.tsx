'use client';
import {Pencil,RefreshCw} from 'lucide-react';
export default function AnswerActions({status,disabled,canGenerate,onEdit,onRegenerate}:{status:string;disabled:boolean;canGenerate:boolean;onEdit:()=>void;onRegenerate:()=>void}){
 if(status!=='done'&&status!=='failed')return null;
 return <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-3 text-xs">
  <button type="button" disabled={disabled} onClick={onEdit} className="flex items-center gap-1.5 font-medium text-slate-600 hover:text-blue-800 disabled:opacity-30"><Pencil size={14}/>编辑问题</button>
  {status==='done'&&<button type="button" disabled={disabled||!canGenerate} onClick={onRegenerate} title="追加同一问题的新回答，保留原答案" className="flex items-center gap-1.5 font-medium text-slate-600 hover:text-blue-800 disabled:opacity-30"><RefreshCw size={14}/>重新生成答案</button>}
 </div>;
}
