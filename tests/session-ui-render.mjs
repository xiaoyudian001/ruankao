import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';import ts from 'typescript';import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';
const dir=path.resolve('outputs/session-ui-render');fs.mkdirSync(dir,{recursive:true});const cache=new Map();
const link='data:text/javascript,'+encodeURIComponent("import React from 'react';export default function Link({children,prefetch,...props}){return React.createElement('a',props,children)}");
function compile(file){file=path.resolve(file);if(cache.has(file))return cache.get(file);const out=path.join(dir,path.relative(process.cwd(),file).replaceAll(path.sep,'-').replace(/\.tsx?$/,'.mjs')),href=pathToFileURL(out).href;cache.set(file,href);
 let code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
 code=code.replace(/from\s+(['"])([^'"]+)\1/g,(match,quote,spec)=>{if(spec==='next/link')return 'from '+JSON.stringify(link);if(!spec.startsWith('.'))return match;const base=path.resolve(path.dirname(file),spec),found=[base,base+'.ts',base+'.tsx'].find(f=>fs.existsSync(f)&&fs.statSync(f).isFile());if(!found)throw Error('Import not found: '+base);return 'from '+JSON.stringify(compile(found));});fs.writeFileSync(out,code);return href;
}
// Link uses the same React installation, rather than resolving an npm import from a data URL.
const linkFile=path.join(dir,'link.mjs');fs.writeFileSync(linkFile,"import React from 'react';export default function Link({children,prefetch,...props}){return React.createElement('a',props,children)}");
const render=(Component,props)=>renderToStaticMarkup(React.createElement(Component,props));
const {default:Sidebar}=await import(compile('app/textbook/session-sidebar.tsx'));
let html=render(Sidebar,{selected:null,disabled:false,refreshKey:'test',onSelect:()=>{},onDeleted:()=>{}});assert.ok(html.includes('搜索标题或问答内容'));assert.ok(html.includes('新建会话'));assert.ok(html.includes('历史会话'));
const {default:Screenshot}=await import(compile('app/textbook/screenshot-input.tsx'));
html=render(Screenshot,{enabled:true,disabled:false,initialAttachment:{id:'11111111-1111-4111-8111-111111111111',confirmed:true},onAttachment:()=>{},onRecognized:()=>{},onBusy:()=>{}});assert.ok(html.includes('正在恢复已识别截图'));assert.ok(html.includes('不覆盖你已编辑的题目文字'));assert.ok(html.includes('移除截图关联'));
// Patch only the platform navigation adapter; the actual chat and draft hook are rendered.
const chatUrl=compile('app/textbook/textbook-chat.tsx'),chatFile=path.resolve(dir,'app-textbook-textbook-chat.mjs');fs.writeFileSync(chatFile,fs.readFileSync(chatFile,'utf8').replace(JSON.stringify(link),JSON.stringify(pathToFileURL(linkFile).href)));
const {default:Chat}=await import(chatUrl);html=render(Chat,{ownerId:'isolated-test-owner'});assert.ok(html.includes('清空草稿'));assert.ok(html.includes('草稿仅保存在当前浏览器'));assert.ok(html.includes('搜索标题或问答内容'));assert.ok(html.includes('发送问题'));
assert.ok(html.includes('导出 Markdown'));
const {default:AnswerActions}=await import(compile('app/textbook/answer-actions.tsx'));
html=render(AnswerActions,{status:'done',disabled:false,canGenerate:true,onEdit:()=>{},onRegenerate:()=>{}});assert.ok(html.includes('编辑问题'));assert.ok(html.includes('重新生成答案'));
html=render(AnswerActions,{status:'failed',disabled:false,canGenerate:true,onEdit:()=>{},onRegenerate:()=>{}});assert.ok(html.includes('编辑问题'));assert.ok(!html.includes('重新生成答案'));
html=render(AnswerActions,{status:'running',disabled:false,canGenerate:true,onEdit:()=>{},onRegenerate:()=>{}});assert.equal(html,'');
assert.ok(fs.existsSync('app/textbook/streaming-answer.tsx'),'missing streaming answer UI');
const {default:StreamingAnswer}=await import(compile('app/textbook/streaming-answer.tsx'));
html=render(StreamingAnswer,{job:{status:'running',partial_answer:'增量正文[片段1]',cancel_requested:0},busy:false,onStop:()=>{}});assert.ok(html.includes('增量正文'));assert.ok(html.includes('停止生成'));assert.ok(!html.includes('href='));
html=render(StreamingAnswer,{job:{status:'cancelled',partial_answer:'已收到的正文',cancel_requested:1},busy:false,onStop:()=>{}});assert.ok(html.includes('已停止'));assert.ok(html.includes('未完成'));assert.ok(!html.includes('停止生成'));
html=render(AnswerActions,{status:'cancelled',disabled:false,canGenerate:true,onEdit:()=>{},onRegenerate:()=>{}});assert.ok(html.includes('编辑问题'));assert.ok(html.includes('重新生成答案'));
console.log(JSON.stringify({passed:true,checks:['search_controls','restored_attachment','keep_corrected_question','clear_draft','server_render_safe']}));
