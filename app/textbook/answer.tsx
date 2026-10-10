import { Fragment, type ReactNode } from 'react';

function inline(text: string,onCitation?: (rank:number)=>void,ranks:number[]=[]): ReactNode {
  const citations=(value:string)=>value.split(/(\[片段\d+(?:[，,][^\]\n]*)?\])/g).map((part,i)=>{
    const rank=Number(part.match(/^\[片段(\d+)(?:[，,]|\])/u)?.[1]);
    return onCitation&&ranks.includes(rank)?<button key={i} type="button" onClick={()=>onCitation(rank)} title="查看原 PDF 页和本次检索片段" className="inline rounded bg-blue-50 px-1 text-left font-medium text-[#173f8a] underline decoration-blue-200 underline-offset-4 hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-blue-700">{part}</button>:<Fragment key={i}>{part}</Fragment>;
  });
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part,i)=>part.startsWith('**')?<strong key={i}>{citations(part.slice(2,-2))}</strong>:part.startsWith('`')?<code key={i} className="rounded bg-slate-100 px-1 py-0.5 text-sm">{part.slice(1,-1)}</code>:<Fragment key={i}>{citations(part)}</Fragment>);
}

export default function Answer({text,onCitation,citationRanks=[]}:{text:string;onCitation?:(rank:number)=>void;citationRanks?:number[]}) {
  const renderInline=(text:string)=>inline(text,onCitation,citationRanks);
  const lines=text.split('\n'); const blocks:ReactNode[]=[];
  for(let i=0;i<lines.length;i++) {
    const line=lines[i].trim(); if(!line)continue;
    if(line.startsWith('|') && /^\|?[\s:|\-]+\|?$/.test(lines[i+1]?.trim()??'')) {
      const rows=[line];i+=2;while(i<lines.length&&lines[i].trim().startsWith('|'))rows.push(lines[i++].trim());i--;
      const cells=(row:string)=>row.replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
      blocks.push(<div key={i} className="my-4 overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><thead><tr>{cells(rows[0]).map((c,j)=><th key={j} className="border border-slate-200 bg-slate-50 p-3">{renderInline(c)}</th>)}</tr></thead><tbody>{rows.slice(1).map((r,j)=><tr key={j}>{cells(r).map((c,k)=><td key={k} className="border border-slate-200 p-3 align-top">{renderInline(c)}</td>)}</tr>)}</tbody></table></div>);continue;
    }
    if(line.startsWith('```')){const code:string[]=[];while(++i<lines.length&&!lines[i].trim().startsWith('```'))code.push(lines[i]);blocks.push(<pre key={i} className="my-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-100"><code>{code.join('\n')}</code></pre>);continue;}
    const heading=line.match(/^#{1,6}\s+(.+)$/);
    if(heading){blocks.push(<h3 key={i} className="mb-3 mt-6 text-lg font-bold first:mt-0">{renderInline(heading[1])}</h3>);continue;}
    if(/^[-*]\s+/.test(line)||/^\d+[.)、]\s*/.test(line)){blocks.push(<div key={i} className="my-2 flex gap-3"><span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-700"/><p>{renderInline(line.replace(/^[-*]\s+/,''))}</p></div>);continue;}
    if(line.startsWith('>')){blocks.push(<blockquote key={i} className="my-3 border-l-4 border-blue-200 bg-blue-50/50 px-4 py-2">{renderInline(line.replace(/^>\s*/,''))}</blockquote>);continue;}
    if(/^[-*_]{3,}$/.test(line)){blocks.push(<hr key={i} className="my-6 border-slate-200"/>);continue;}
    blocks.push(<p key={i} className="my-2 whitespace-pre-wrap">{renderInline(line)}</p>);
  }
  return <div className="min-w-0 break-words text-base leading-8 text-slate-800">{blocks}</div>;
}
