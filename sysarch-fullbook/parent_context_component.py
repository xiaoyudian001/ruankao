"""Self-contained Langflow parent expansion with a safe retrieval-only fallback."""
from pathlib import Path

HERE=Path(__file__).parent
PURE='\n\n'.join((HERE/name).read_text(encoding='utf-8') for name in
                ['citation_format.py','formula_evidence.py','parent_context.py'])
PURE=PURE.replace('from citation_format import source_hint\n','').replace('from formula_evidence import enrich_formula_evidence\n','')

PARENT_CODE=PURE+'''

from lfx.custom import Component
from lfx.io import HandleInput, StrInput, IntInput, BoolInput, Output
from lfx.schema.dataframe import DataFrame


class TextbookParentContext(Component):
    display_name = '父级上下文扩展'
    description = '命中子片段后补充标题边界内的前后原文；来源去重、预算限制、保留独立引用页码。'
    icon = 'Layers'
    name = 'TextbookParentContext'
    inputs = [
        HandleInput(name='hits',display_name='检索/重排后的片段',input_types=['DataFrame','Table'],required=True),
        BoolInput(name='enabled',display_name='启用上下文扩展',value=True,advanced=True),
        IntInput(name='max_chars',display_name='上下文字符预算',value=10000,advanced=True),
        IntInput(name='max_sources',display_name='最多引用片段',value=10,advanced=True),
        StrInput(name='index_path',display_name='父级索引路径',required=True,advanced=True),
        StrInput(name='index_sha256',display_name='索引SHA256',required=True,advanced=True),
    ]
    outputs = [Output(name='expanded_context',display_name='带来源的完整上下文',method='expand')]

    def expand(self) -> DataFrame:
        hits=self.hits.to_dict(orient='records')
        try:
            if not self.enabled:raise ValueError('ExpansionDisabled')
            index=load_parent_index(self.index_path,self.index_sha256)
            rows,trace=expand_context(hits,index,max_chars=int(self.max_chars),max_rows=int(self.max_sources))
        except Exception as error:
            rows=[{**enrich_formula_evidence(r),'rag_rank':i,'context_role':'hit',
                   'context_hit_ranks':[i],'context_title':str(r.get('chapter','')),
                   'context_hint':'直接命中'} for i,r in enumerate(hits,1)]
            trace={'version':VERSION,'route':'retrieval_only_fallback','reason':type(error).__name__,
                   'hit_count':len(hits),'added_count':0,'context_chars':sum(_cost(r) for r in rows)}
        self.status=json.dumps(trace,ensure_ascii=False)
        if rows:rows[0]['context_expansion_trace']=trace
        return DataFrame(rows) if rows else DataFrame({'content':[],'rag_rank':[],'context_hint':[]})
'''
