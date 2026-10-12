import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
import ts from 'typescript';import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';
const dir=path.resolve('outputs/case-render');fs.mkdirSync(dir,{recursive:true});
function compile(file,replacements={}){let code=fs.readFileSync(file,'utf8');for(const [a,b]of Object.entries(replacements))code=code.replaceAll(a,b);const p=path.join(dir,path.basename(file).replace('.tsx','.mjs'));fs.writeFileSync(p,ts.transpileModule(code,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);return pathToFileURL(p).href;}
const answer=compile('app/textbook/answer.tsx'),critic=compile('app/review/critique-panel.tsx');
const {CaseExercise}=await import(compile('app/cases/case-study.tsx',{'next/link':'next/link.js','../textbook/answer':answer,'../review/critique-panel':critic,'../textbook/source-panel':compile('app/textbook/source-panel.tsx')}));
const ref={rank:1,label:'教材页',pdfPages:[427],chapter:'第12章'};
const q={id:'q',ordinal:1,prompt:'为什么复用？',jobId:'j',attempts:[],analysis:{answer:'秘密参考分析[片段1]',references:[ref]}};
const props={question:q,draft:'',busy:false,ready:true,onDraft:()=>{},onSubmit:()=>{},onCitation:()=>{}};
let html=renderToStaticMarkup(React.createElement(CaseExercise,props));assert.ok(!html.includes('秘密参考分析'));assert.ok(html.includes('先写下自己的答案'));
const feedback={summary:'总体反馈',correct:[],missing:[{point:'遗漏业务条件',ranks:[1]}],corrections:[],suggestion:'补充条件',insufficientEvidence:false};
html=renderToStaticMarkup(React.createElement(CaseExercise,{...props,question:{...q,attempts:[{id:'a',response:'我写的答案',status:'done',createdAt:1,critique:{id:'a',status:'done',error:null,result:feedback}}]}}));
assert.ok(html.includes('秘密参考分析'));assert.ok(html.includes('遗漏业务条件'));assert.ok(html.includes('修改后再次点评'));assert.ok(html.includes('查看点评依据片段1'));assert.ok(html.includes('我写的答案'));
console.log(JSON.stringify({passed:true,checks:['answer_hidden','submitted_response','reference_analysis','missing_points','clickable_citation','revision_action']}));
