"""Focused JSX edits without rewriting unrelated site layout."""
from pathlib import Path
path=Path(r'F:\daily\ruankao-40-day\app\textbook\textbook-chat.tsx')
text=path.read_text(encoding='utf-8')
changes=[
    ('/>教材助手</b>','/>教材助手 <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">{RETRIEVAL_MODES[m.retrieval_mode??\'default\']}</span></b>'),
    ('onClick={()=>void send(m.question)}','onClick={()=>void send(m.question,m.retrieval_mode??\'default\')}'),
    ('disabled={!online||sending||pending} onClick={()=>void send(m.question',
     'disabled={!online||sending||pending||!availableModes.includes(m.retrieval_mode??\'default\')} onClick={()=>void send(m.question'),
    ('<label htmlFor="textbook-question"',
     '''<div className="mb-3 flex flex-wrap items-center gap-3"><label htmlFor="retrieval-mode" className="text-sm font-medium text-slate-600">检索模式</label><select id="retrieval-mode" value={mode} disabled={sending||pending} onChange={e=>{setMode(e.target.value as RetrievalMode);request.current=null;setNotice('');}} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">{(Object.keys(RETRIEVAL_MODES) as RetrievalMode[]).map(key=><option key={key} value={key} disabled={!availableModes.includes(key)}>{RETRIEVAL_MODES[key]}{!availableModes.includes(key)?'（暂不可用）':''}</option>)}</select><span className="text-xs text-slate-500">{mode==='complete'?'复杂问题按需拆分，混合检索后本地重排；耗时可能增加。':'使用当前稳定问答流程。'}</span></div><label htmlFor="textbook-question"'''),
    ('disabled={!online||sending||pending||!draft.trim()}','disabled={!online||sending||pending||!availableModes.includes(mode)||!draft.trim()}')]
for old,new in changes:
    assert text.count(old)==1,old
    text=text.replace(old,new)
path.write_text(text,encoding='utf-8')
print('Mode selector, per-answer labels and retry mode wired')
