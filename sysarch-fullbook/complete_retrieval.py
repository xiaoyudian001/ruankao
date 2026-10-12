"""Bounded local rerank selection preserving available subquery coverage."""
import math
import re
import json
from rerank_retrieval import candidate_rows, final_limit
from subquery_retrieval import fallback_plan, explicit_chapters, parse_plan


def comparison_fallback(question, reason):
    """Extract only a plain two-object comparison; otherwise retain existing fallback."""
    default=fallback_plan(question,reason)
    if explicit_chapters(question):return default
    match=re.fullmatch(r'\s*([\u3400-\u9fffA-Za-z0-9_-]{1,40})[与和]([\u3400-\u9fffA-Za-z0-9_-]{1,40})(?:有什么区别|有什么不同|的区别)([\s\S]*)',question)
    if not match:return default
    a,b,tail=match.groups()
    if a==b:return default
    residue=re.sub(r'依据|根据|教材|比较|描述重点|重点|分别|解释|说明|请|的|是什么|[\s。？?，,；;！!]','',tail)
    if residue:return default
    aspect='描述重点' if '描述重点' in tail else '定义'
    try:
        plan=parse_plan(question,json.dumps({'queries':[{'query':f'{a}的{aspect}是什么？','chapter':None},
                                                      {'query':f'{b}的{aspect}是什么？','chapter':None}]},ensure_ascii=False))
    except ValueError:return default
    plan['reason']='extractive_comparison_fallback:'+reason
    return plan


def coverage_select(rows, scores, queries, final_k=5):
    rows = candidate_rows(rows)
    final_k = final_limit(final_k)
    if not queries or len(queries)>3 or len(set(queries))!=len(queries) or final_k<len(queries):
        raise ValueError('Expected 1..3 unique queries within final budget')
    known=set(queries)
    for row in rows:
        labels=row.get('coverage_labels',row.get('matched_queries'))
        if not isinstance(labels,list) or not labels or not set(labels)<=known:
            raise ValueError('Candidate labels differ from validated query plan')
    if scores is not None:
        if len(scores)!=len(rows) or any(isinstance(s,bool) or not isinstance(s,(int,float)) or not math.isfinite(s) for s in scores):
            raise ValueError('Expected one finite local logit per candidate')
        ranking=sorted(range(len(rows)),key=lambda i:(-scores[i],i))
    else:
        ranking=list(range(len(rows)))
    selected=set()
    # An already selected shared passage can satisfy more than one query.
    for query in queries:
        if any(query in rows[i].get('coverage_labels',rows[i]['matched_queries']) for i in selected):
            continue
        best=next((i for i in ranking if query in rows[i].get('coverage_labels',rows[i]['matched_queries'])),None)
        if best is not None:selected.add(best)
    for i in ranking:
        if len(selected)>=final_k:break
        selected.add(i)
    selected=[i for i in ranking if i in selected]
    return [{**rows[i], 'rrf_pool_rank': i+1, 'rerank_score': float(scores[i]) if scores is not None else None,
             'rag_rank': rank, 'rerank_method': 'local_cross_encoder_coverage' if scores is not None else 'rrf_coverage_fallback',
             'retrieval_method': 'subquery+bm25+dense+rrf+local-rerank+coverage'}
            for rank,i in enumerate(selected,1)]
