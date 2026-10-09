// Caller supplies only server-selected completed rows, newest first.
export function historySnapshot(rows: {question:string;answer:string}[]): string {
  return JSON.stringify(rows.slice(0,3).reverse().map(row=>({
    question:row.question.trim().slice(0,2000),
    answer:row.answer.replace(/<think\b[^>]*>[\s\S]*?(?:<\/think\s*>|$)/gi,'').trim().slice(0,1000),
  })).filter(row=>row.question&&row.answer));
}
export function rewriteDiagnostic(body:Record<string,unknown>): {query:string|null;route:string|null} {
  if(body.retrievalQuery==null&&body.rewriteRoute==null)return {query:null,route:null};
  if(typeof body.rewriteRoute!=='string'||!['direct','rewritten','clarification'].includes(body.rewriteRoute))throw new Error('Invalid rewrite route');
  if(typeof body.retrievalQuery!=='string'||body.retrievalQuery.length>2000||/[\r\n<>]/.test(body.retrievalQuery))throw new Error('Invalid search question');
  const query=body.retrievalQuery.trim();
  if(body.rewriteRoute!=='clarification'&&!query)throw new Error('Missing search question');
  return {query:query||null,route:body.rewriteRoute};
}
