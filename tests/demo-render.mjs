import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

const dir=path.resolve('outputs/demo-render');fs.mkdirSync(dir,{recursive:true});
const url=f=>pathToFileURL(path.resolve(f)).href;
function compile(file,replace={}){
  let code=fs.readFileSync(file,'utf8');
  for(const [a,b]of Object.entries(replace))code=code.replaceAll(a,b);
  const out=path.join(dir,path.basename(file).replace(/\.tsx?$/,'.mjs'));
  fs.writeFileSync(out,ts.transpileModule(code,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText);
  return pathToFileURL(out).href;
}
assert.ok(fs.existsSync('app/demo/page.tsx'),'公开演示路由尚未实现');
const content=await import(url('lib/demo/content.ts'));
const ui=await import(compile('app/demo/demo-workspace.tsx',{'../../lib/demo/content':url('lib/demo/content.ts'),'../textbook/answer':compile('app/textbook/answer.tsx')}));
const render=(Component,props={})=>renderToStaticMarkup(React.createElement(Component,props));
const common={onCitation:()=>{},onSubmit:()=>{},onChoose:()=>{}};
const home=render(ui.default);
assert.ok(home.includes('预录演示'));assert.ok(home.includes('无需登录'));assert.ok(home.includes('github.com/xiaoyudian001/ruankao'));
assert.ok(home.includes('教材问答'));assert.ok(home.includes('案例练习'));assert.ok(home.includes('论文训练'));
assert.ok(!home.includes('href="/"'),'演示访客不应被导航到仍使用共享数据的复习首页');
const question=render(ui.QuestionExample,common);assert.ok(question.includes('查看自写原页'));
let html=render(ui.CaseExample,{...common,revision:0,revealed:false});
assert.ok(!html.includes(content.CASE.drafts[0].feedback));assert.ok(html.includes('提交示例答案'));
html=render(ui.CaseExample,{...common,revision:0,revealed:true});assert.ok(html.includes('缺少的要点'));
const improved=render(ui.CaseExample,{...common,revision:1,revealed:true});assert.ok(improved.includes('边界说明已补充'));assert.notEqual(html,improved);
html=render(ui.EssayExample,{...common,revision:0,revealed:true,outlineVisible:true,onOutline:()=>{}});assert.ok(html.includes('不能把示例当作真实项目经历'));assert.ok(html.includes('缺少方案取舍'));
html=render(ui.EssayExample,{...common,revision:1,revealed:true,outlineVisible:false,onOutline:()=>{}});assert.ok(html.includes('尚未提供实测指标'));
for(const source of content.SOURCES){
  html=render(ui.DemoSource,{source,onClose:()=>{}});
  assert.ok(html.includes('自写学习笔记'));assert.ok(html.includes(source.title));assert.ok(html.includes('返回演示'));
}
for(const answer of [content.QUESTION.answer,...content.CASE.drafts.map(x=>x.feedback),content.ESSAY.outline,...content.ESSAY.drafts.map(x=>x.feedback)]){
  for(const match of answer.matchAll(/\[片段(\d+)\]/g))assert.ok(content.SOURCES.some(x=>x.rank===Number(match[1])),'引用必须有公开样例来源');
}
// Public demo must stay independent of private auth, API and model processing.
for(const file of ['app/demo/page.tsx','app/demo/demo-workspace.tsx','lib/demo/content.ts']){
  const code=fs.readFileSync(file,'utf8');assert.ok(!/fetch\s*\(|\/api\/|requireChatGPTUser|runtime\(|localStorage|process\.env/.test(code),file+'不可访问私有学习数据或实时服务');
}
console.log(JSON.stringify({passed:true,checks:['public_route','three_scenarios','submit_before_feedback','revision_specific_feedback','authored_sources','no_private_dependencies']}));
