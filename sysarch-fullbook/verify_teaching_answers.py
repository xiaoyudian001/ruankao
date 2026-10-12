"""Exercise the updated saved flow with isolated, non-stored questions."""
import json, sys, time, uuid
from pathlib import Path
sys.path.insert(0,r'F:\daily\textbook-bridge')
from bridge import LocalFlow

root=Path(r'F:\daily\output\sysarch-teaching-prompt')
cases=[
 ('definition','解释一下什么是MTBF，并指出教材出处。'),
 ('duties','系统架构设计师有哪些职责？请归纳要点并注明教材出处。'),
 ('comparison','MTBF和MTTR有什么区别？先按教材说明并注明出处，再用一个明确标为假设的简单例子帮助理解。'),
]
results=[]
for name,question in cases:
 start=time.monotonic()
 answer=LocalFlow().run({'question':question,'session_id':str(uuid.uuid4())})
 (root/f'{name}-answer.md').write_text('# '+question+'\n\n'+answer,encoding='utf-8')
 result={'name':name,'elapsed_ms':round((time.monotonic()-start)*1000),'answer_nonempty':bool(answer),'think_removed':'<think' not in answer,'has_citation':'[片段' in answer,'has_book_and_pdf_pages':'教材第' in answer and 'PDF第' in answer}
 results.append(result)
 print(json.dumps(result,ensure_ascii=False),flush=True)
 assert result['answer_nonempty'] and result['think_removed'] and result['has_citation'] and result['has_book_and_pdf_pages']
(root/'answer-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
