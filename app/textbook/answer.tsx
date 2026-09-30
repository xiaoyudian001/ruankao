import { Fragment, type ReactNode } from 'react';

function inline(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part,i)=>part.startsWith('**')?<strong key={i}>{part.slice(2,-2)}</strong>:part.startsWith('`')?<code key={i} className="rounded bg-slate-100 px-1 py-0.5 text-sm">{part.slice(1,-1)}</code>:<Fragment key={i}>{part}</Fragment>);
}

export default function Answer({text}:{text:string}) {
  const lines=text.split('\n'); const blocks:ReactNode[]=[];
  for(let i=0;i<lines.length;i++) {
    const line=lines[i].trim(); if(!line)continue;
    if(line.startsWith('|') && /^\|?[\s:|\-]+\|?$/.test(lines[i+1]?.trim()??'')) {
      const rows=[line];i+=2;while(i<lines.length&&lines[i].trim().startsWith('|'))rows.push(lines[i++].trim());i--;
      const cells=(row:string)=>row.replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
      blocks.push(<div key={i} className="my-4 overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><thead><tr>{cells(rows[0]).map((c,j)=><th key={j} className="border border-slate-200 bg-slate-50 p-3">{inline(c)}</th>)}</tr></thead><tbody>{rows.slice(1).map((r,j)=><tr key={j}>{cells(r).map((c,k)=><td key={k} className="border border-slate-200 p-3 align-top">{inline(c)}</td>)}</tr>)}</tbody></table></div>);continue;
    }
    if(line.startsWith('```')){const code:string[]=[];while(++i<lines.length&&!lines[i].trim().startsWith('```'))code.push(lines[i]);blocks.push(<pre key={i} className="my-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-100"><code>{code.join('\n')}</code></pre>);continue;}
    const heading=line.match(/^#{1,6}\s+(.+)$/);
    if(heading){blocks.push(<h3 key={i} className="mb-3 mt-6 text-lg font-bold first:mt-0">{inline(heading[1])}</h3>);continue;}
    if(/^[-*]\s+/.test(line)||/^\d+[.)、]\s*/.test(line)){blocks.push(<div key={i} className="my-2 flex gap-3"><span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-700"/><p>{inline(line.replace(/^[-*]\s+/,''))}</p></div>);continue;}
    if(line.startsWith('>')){blocks.push(<blockquote key={i} className="my-3 border-l-4 border-blue-200 bg-blue-50/50 px-4 py-2">{inline(line.replace(/^>\s*/,''))}</blockquote>);continue;}
    if(/^[-*_]{3,}$/.test(line)){blocks.push(<hr key={i} className="my-6 border-slate-200"/>);continue;}
    blocks.push(<p key={i} className="my-2 whitespace-pre-wrap">{inline(line)}</p>);
  }
  return <div className="min-w-0 break-words text-base leading-8 text-slate-800">{blocks}</div>;
}
