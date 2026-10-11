export const TASK_TYPES={qa:'教材问答',exam:'真题解析'} as const;
export type TaskType=keyof typeof TASK_TYPES;
export type Practice={question:string;options:{label:string;text:string}[];correct:string;explanation:string;ranks:number[]};
export type PracticeView=Pick<Practice,'question'|'options'>&{choice?:string;correct?:string;isCorrect?:boolean;explanation?:string;ranks?:number[]};
export function validTaskType(value:unknown):TaskType{
 if(value==null)return 'qa';
 if(value!=='qa'&&value!=='exam')throw new Error('题目类型无效。');
 return value;
}
export const sameTaskRequest=(prior:unknown,next:TaskType)=>(prior??'qa')===next;
export function validatePractice(value:unknown,ranks:number[]):Practice|null{
 if(value==null)return null;
 const text=(v:unknown,max:number)=>{if(typeof v!=='string'||!v.trim()||v.length>max||/<\/?(?:think|script|iframe)\b/i.test(v))throw new Error('Invalid practice text');return v.trim();};
 if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('Invalid practice');
 const p=value as Record<string,unknown>;
 if(Object.keys(p).sort().join(',')!=='correct,explanation,options,question,ranks')throw new Error('Invalid practice fields');
 if(!Array.isArray(p.options)||p.options.length!==4||typeof p.correct!=='string'||!['A','B','C','D'].includes(p.correct))throw new Error('Invalid practice options');
 const options=p.options.map((o,i)=>{if(!o||typeof o!=='object'||o.label!=='ABCD'[i])throw new Error('Invalid option label');return {label:o.label as string,text:text(o.text,1000)};});
 if(new Set(options.map(o=>o.text.replace(/\s/g,''))).size!==4)throw new Error('Duplicate options');
 if(!Array.isArray(p.ranks)||!p.ranks.length||p.ranks.length>10||p.ranks.some(r=>!Number.isInteger(r)||!ranks.includes(r))||new Set(p.ranks).size!==p.ranks.length)throw new Error('Invalid practice source');
 const explanation=text(p.explanation,4000);
 if([...explanation.matchAll(/\[片段(\d+)/g)].some(m=>!(p.ranks as number[]).includes(Number(m[1]))))throw new Error('Invalid practice citation');
 return {question:text(p.question,2000),options,correct:p.correct,explanation,ranks:p.ranks as number[]};
}
export function practiceView(practice:Practice|null,choice:unknown):PracticeView|null{
 if(!practice)return null;
 const view={question:practice.question,options:practice.options};
 if(choice==null)return view;
 if(typeof choice!=='string'||!practice.options.some(o=>o.label===choice))throw new Error('Invalid submitted option');
 return {...view,choice,correct:practice.correct,isCorrect:choice===practice.correct,explanation:practice.explanation,ranks:practice.ranks};
}
export function savedPractice(value:unknown,ranks:number[]):Practice|null{
 if(value==null)return null;
 return validatePractice(typeof value==='string'?JSON.parse(value):value,ranks);
}
