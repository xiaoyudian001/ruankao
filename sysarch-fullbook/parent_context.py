"""Bounded parent windows over immutable, ordered textbook child passages."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from citation_format import source_hint
from formula_evidence import enrich_formula_evidence

BOOK_SHA = 'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'
VERSION = 'sysarch-parent-window-v1'


def _check_row(row):
    if row.get('source_sha256') != BOOK_SHA or row.get('section_type') != 'body':
        raise ValueError('Expected the verified textbook body')
    if not re.fullmatch(r'[a-f0-9]{64}',str(row.get('chunk_id',''))) or not isinstance(row.get('content'),str) or not row['content'].strip():
        raise ValueError('Expected immutable child identity and text')
    first,last=int(row['pdf_page_start']),int(row['pdf_page_end'])
    pages=[int(p) for p in str(row['pdf_pages']).split(',')]
    if not 1<=first<=last<=728 or last-first>5 or pages!=list(range(first,last+1)):
        raise ValueError('Expected bounded contiguous PDF pages')


def build_parent_index(ordered_rows):
    entries=[]; seen=set(); title=''; chapter=None; previous_page=0
    for raw in ordered_rows:
        row=dict(raw); _check_row(row)
        if row['chunk_id'] in seen or int(row['pdf_page_start'])<previous_page:
            raise ValueError('Expected unique children in source order')
        seen.add(row['chunk_id']);previous_page=int(row['pdf_page_start'])
        current_chapter=str(row.get('chapter',''))
        if current_chapter!=chapter:
            chapter=current_chapter;title=chapter
        headings=list(re.finditer(r'^#{1,6}[ \t]+([^\n]+)',row['content'],re.M))
        start_title=title
        if headings and not row['content'][:headings[0].start()].strip():
            start_title=headings[0][1].strip()
        end_title=headings[-1][1].strip() if headings else start_title
        row_title=' / '.join(dict.fromkeys([start_title]+[h[1].strip() for h in headings]))[:200]
        entries.append({'row':row,'start_title':start_title,'end_title':end_title,'title':row_title})
        title=end_title
    if not entries:
        raise ValueError('Parent corpus is empty')

    def continuous(left,right):
        a,b=left['row'],right['row']
        return (bool(str(a.get('chapter','')).strip()) and a.get('chapter')==b.get('chapter')
                and left['end_title']==right['start_title']
                and 0<=int(b['pdf_page_start'])-int(a['pdf_page_end'])<=1)

    parents={}; children={}
    for i,entry in enumerate(entries):
        positions=[i]
        if i>0 and continuous(entries[i-1],entry):positions.insert(0,i-1)
        if i+1<len(entries) and continuous(entry,entries[i+1]):positions.append(i+1)
        ids=[entries[p]['row']['chunk_id'] for p in positions]
        parent_id=hashlib.sha256((VERSION+'|'+BOOK_SHA+'|'+'|'.join(ids)).encode()).hexdigest()
        parent_title=' / '.join(dict.fromkeys(entries[p]['title'] for p in positions))[:200]
        parents[parent_id]={'child_ids':ids,'title':parent_title}
        children[entry['row']['chunk_id']]={'row':entry['row'],'parent_id':parent_id,'title':entry['title']}
    return {'version':VERSION,'book_sha':BOOK_SHA,'children':children,'parents':parents,'count':len(children)}


def _cost(row):
    # Same fields and separator as the Parser input, including reviewed formula evidence.
    return len(f"[片段{row['rag_rank']}]\n{source_hint(row)}\n{row['context_hint']}\n{row['content']}\n\n")


def expand_context(hits,index,max_chars=10000,max_rows=10):
    if index.get('version')!=VERSION or index.get('book_sha')!=BOOK_SHA:
        raise ValueError('Parent index identity differs')
    if not isinstance(max_chars,int) or not 100<=max_chars<=12000 or not 1<=max_rows<=10:
        raise ValueError('Invalid context budget')
    if len(hits)>5 or len({r.get('chunk_id') for r in hits})!=len(hits):
        raise ValueError('Expected at most five distinct retrieval hits')
    output=[]; candidate_hits={}; candidate_parents={}; rounds=[]
    for rank,hit in enumerate(hits,1):
        _check_row(hit)
        entry=index['children'].get(hit['chunk_id'])
        if not entry or any(str(hit.get(k,''))!=str(entry['row'].get(k,'')) for k in
                            ('content','source_sha256','pdf_pages','pdf_page_start','pdf_page_end','chapter')):
            raise ValueError('Retrieval child differs from the parent corpus')
        parent=index['parents'][entry['parent_id']]
        row=enrich_formula_evidence(hit)
        row.update(rag_rank=rank,context_role='hit',context_hit_ranks=[rank],
                   parent_window_id=entry['parent_id'],context_title=entry['title'],
                   context_hint='直接命中；所属标题：'+entry['title'])
        output.append(row)
        candidates=[cid for cid in parent['child_ids'] if cid!=hit['chunk_id']]
        rounds.append(candidates)
        for cid in candidates:
            candidate_hits.setdefault(cid,[]).append(rank)
            candidate_parents.setdefault(cid,[]).append(entry['parent_id'])
    selected={r['chunk_id'] for r in output}; cost=sum(_cost(r) for r in output)
    skipped=[]
    # One neighbor per hit per pass prevents the first parent consuming the entire budget.
    for distance in range(max((len(c) for c in rounds),default=0)):
        for candidates in rounds:
            if distance>=len(candidates):continue
            cid=candidates[distance]
            if cid in selected:continue
            entry=index['children'][cid]
            row=enrich_formula_evidence(entry['row'])
            related=candidate_hits[cid]
            row.update(rag_rank=len(output)+1,context_role='neighbor',context_hit_ranks=related,
                       parent_window_id=entry['parent_id'],context_title=entry['title'],
                       context_hint='相邻上下文，关联'+''.join(f'[片段{r}]' for r in related)+'；所属标题：'+entry['title'])
            if len(output)>=max_rows or cost+_cost(row)>max_chars:
                skipped.append(cid);continue
            output.append(row);selected.add(cid);cost+=_cost(row)
    trace={'version':VERSION,'route':'expanded' if len(output)>len(hits) else 'unchanged',
           'hit_count':len(hits),'added_count':len(output)-len(hits),'context_chars':cost,
           'max_chars':max_chars,'max_rows':max_rows,'base_over_budget':cost>max_chars and len(output)==len(hits),
           'skipped_count':len(set(skipped)),'hit_ids':[r['chunk_id'] for r in hits],
           'added_ids':[r['chunk_id'] for r in output[len(hits):]],
           'parents':[index['children'][r['chunk_id']]['parent_id'] for r in hits]}
    return output,trace


@lru_cache(maxsize=2)
def _decode_index(raw):
    index=json.loads(raw)
    if index.get('version')!=VERSION or index.get('book_sha')!=BOOK_SHA or index.get('count')!=len(index.get('children',{})):
        raise ValueError('Invalid parent index')
    return index


def load_parent_index(path,expected_sha):
    resolved=Path(path).resolve();root=Path(r'F:\daily\output\sysarch-parent-context').resolve()
    if root not in resolved.parents or not re.fullmatch(r'[a-f0-9]{64}',expected_sha):
        raise ValueError('Unexpected parent index path or SHA256')
    raw=resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('Parent index SHA256 differs')
    return _decode_index(raw)
