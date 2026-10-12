import type {SourceSummary} from '../textbook/sources';
export const SECTIONS={abstract:'摘要',background:'项目背景与职责',design:'架构方案与技术选择',implementation:'实施过程与问题解决',conclusion:'效果、反思与总结'} as const;
export type Section=keyof typeof SECTIONS;
export type EssayInput={title:string;topic:string;requirements:string;projectFacts:string;drafts:Record<Section,string>};
export type EssayRun={id:string;kind:'outline'|'feedback';section:string;draft:string;projectFacts:string;topic:string;requirements:string;version:number;status:string;answer:string|null;error:string|null;references:SourceSummary[];createdAt:number};
export type Essay=EssayInput&{id:string;version:number;updatedAt:number;runs:EssayRun[]};
export type EssaySummary={id:string;title:string;topic:string;updatedAt:number};
export function restoreEssayDraft(raw:unknown):EssayInput{
 const v=raw&&typeof raw==='object'?raw as Record<string,unknown>:{},d=v.drafts&&typeof v.drafts==='object'?v.drafts as Record<string,unknown>:{};
 const text=(x:unknown,max:number)=>typeof x==='string'?x.slice(0,max):'';
 return {title:text(v.title,100),topic:text(v.topic,1200),requirements:text(v.requirements,2000),projectFacts:text(v.projectFacts,4000),drafts:Object.fromEntries(Object.keys(SECTIONS).map(k=>[k,text(d[k],8000)])) as Record<Section,string>};
}
export function essayInput(raw:unknown):EssayInput{
 if(!raw||typeof raw!=='object')throw new Error('论文材料格式无效。');const v=raw as Record<string,unknown>;
 const text=(s:unknown,max:number,label:string,required=true)=>{if(typeof s!=='string'||s.length>max||(required&&!s.trim()))throw new Error(`${label}${required?'不能为空，':''}最多${max}字。`);return s.trim();};
 const topic=text(v.topic,1200,'论文主题'),projectFacts=text(v.projectFacts,4000,'项目事实');
 const drafts=v.drafts&&typeof v.drafts==='object'&&!Array.isArray(v.drafts)?v.drafts as Record<string,unknown>:{};
 if(Object.keys(drafts).some(k=>!Object.hasOwn(SECTIONS,k)))throw new Error('写作段落无效。');
 return {title:v.title==null||v.title===''?topic.slice(0,60):text(v.title,100,'训练名称'),topic,projectFacts,requirements:text(v.requirements??'',2000,'题目要求',false),drafts:Object.fromEntries(Object.keys(SECTIONS).map(k=>[k,text(drafts[k]??'',8000,'段落稿件',false)])) as Record<Section,string>};
}
export function essayTask(input:EssayInput,version:number,kind:unknown,section?:unknown){
 if(kind!=='outline'&&kind!=='feedback')throw new Error('训练类型无效。');
 if(kind==='feedback'&&(typeof section!=='string'||!Object.hasOwn(SECTIONS,section)))throw new Error('请选择写作段落。');
 const key=section as Section,draft=kind==='feedback'?input.drafts[key]:'';
 if(kind==='feedback'&&!draft.trim())throw new Error('请先写下该段稿件。');
 return {kind,topic:input.topic,requirements:input.requirements,projectFacts:input.projectFacts,version,section:kind==='feedback'?SECTIONS[key]:'',draft};
}
