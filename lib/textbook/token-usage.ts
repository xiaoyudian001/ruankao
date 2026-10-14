export type TokenUsage={scope:'answer_generation';inputTokens:number|null;outputTokens:number|null;totalTokens:number|null;reportedCalls:number;unreportedCalls:number;models:string[]};
export function tokenUsage(value:unknown):TokenUsage|null{
 if(value==null)return null;
 if(typeof value!=='object'||Array.isArray(value))throw new Error('Invalid token usage');
 const v=value as Record<string,unknown>;
 const count=(n:unknown,max:number)=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0&&n<=max;
 if(v.scope!=='answer_generation'||!count(v.reportedCalls,100)||!count(v.unreportedCalls,100))throw new Error('Invalid token usage scope or calls');
 const reported=v.reportedCalls as number,missing=v.unreportedCalls as number;
 if(reported+missing<1||reported+missing>100)throw new Error('Invalid token usage calls');
 const tokens=[v.inputTokens,v.outputTokens,v.totalTokens];
 if(reported?tokens.some(n=>!count(n,100000000))||(tokens[0] as number)+(tokens[1] as number)!==tokens[2]:tokens.some(n=>n!==null))throw new Error('Invalid token usage counts');
 if(!Array.isArray(v.models)||v.models.length>4||v.models.some(m=>typeof m!=='string'||!/^[A-Za-z0-9_.:/ -]{1,100}$/.test(m))||new Set(v.models).size!==v.models.length)throw new Error('Invalid token usage models');
 return {scope:'answer_generation',inputTokens:v.inputTokens as number|null,outputTokens:v.outputTokens as number|null,totalTokens:v.totalTokens as number|null,reportedCalls:reported,unreportedCalls:missing,models:v.models as string[]};
}
export function storedTokenUsage(raw:unknown):TokenUsage|null{
 try{return typeof raw==='string'?tokenUsage(JSON.parse(raw)):null;}catch{return null;}
}
