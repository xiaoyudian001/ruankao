import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {practiceView} from '../lib/textbook/exam.ts';
const dir=path.resolve('outputs/exam-render');fs.mkdirSync(dir,{recursive:true});
function compile(file){let code=fs.readFileSync(file,'utf8').replace("from './answer'","from './answer.mjs'");const out=path.join(dir,path.basename(file).replace('.tsx','.mjs'));fs.writeFileSync(out,ts.transpileModule(code,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);return pathToFileURL(out).href;}
compile('app/textbook/answer.tsx');const {default:Practice}=await import(compile('app/textbook/exam-practice.tsx'));
const data={question:'测试练习题',options:['A','B','C','D'].map(label=>({label,text:'内容'+label})),correct:'A',explanation:'独有的隐藏解析[片段1]',ranks:[1]};
const props={jobId:'id',onSubmitted:()=>{},onCitation:()=>{},citationRanks:[1]};
const hidden=renderToStaticMarkup(React.createElement(Practice,{...props,practice:practiceView(data,null)}));
assert.equal((hidden.match(/type="radio"/g)||[]).length,4);assert.ok(hidden.includes('提交并查看解析'));assert.ok(!hidden.includes('独有的隐藏解析'));assert.ok(!hidden.includes('参考答案'));
const revealed=renderToStaticMarkup(React.createElement(Practice,{...props,practice:practiceView(data,'B')}));
assert.ok(revealed.includes('独有的隐藏解析'));assert.ok(revealed.includes('本题需要再巩固'));assert.ok(revealed.includes('查看原 PDF 页'));assert.ok(!revealed.includes('提交并查看解析'));
console.log(JSON.stringify({passed:true,checks:['four_radio_options','hidden_explanation','reveal_after_submit','citation_button']}));
