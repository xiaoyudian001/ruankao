"""Complete flow composes tested planning/retrieval and offline ranking."""
from pathlib import Path
from subquery_components import PLANNER_CODE, RETRIEVER_CODE
from local_rerank_components import LOCAL_CODE

HERE=Path(__file__).parent
# Reuse the same native retrieval and traces; keep 20 candidates before reranking.
COMPLETE_RETRIEVER_CODE=RETRIEVER_CODE.replace(
    'rows = merge_evidence(queries,[t["fused_candidates"] for t in traces],int(self.final_k))',
    '''rows = merge_evidence(queries,[t["fused_candidates"] for t in traces],20)
        for row in rows:
            row["coverage_labels"] = [json.dumps([q["query"],q["chapter"]],ensure_ascii=False)
                for q,t in zip(queries,traces) if any(r["chunk_id"]==row["chunk_id"] for r in t["fused_candidates"])]''')
assert COMPLETE_RETRIEVER_CODE!=RETRIEVER_CODE
COMPLETE_RETRIEVER_CODE=COMPLETE_RETRIEVER_CODE.replace(
    'description = "同一知识库与正文索引；每个子问题20语义＋20关键词→RRF；分问题轮流选最多5片。"',
    'description = "逐问题20语义＋20关键词→RRF；轮流合并去重最多20候选，交给本地重排。"')

PURE=(HERE/'complete_retrieval.py').read_text(encoding='utf-8').replace(
    'from rerank_retrieval import candidate_rows, final_limit','').replace(
    'from subquery_retrieval import fallback_plan, explicit_chapters, parse_plan','')
COMPLETE_PLANNER_CODE=PLANNER_CODE.replace('class TextbookQueryPlanner',PURE+'\nclass TextbookQueryPlanner')
COMPLETE_PLANNER_CODE=COMPLETE_PLANNER_CODE.replace(
    'result = fallback_plan(self.question, "planner_fallback:" + type(exc).__name__)',
    'result = comparison_fallback(self.question, "planner_fallback:" + type(exc).__name__)').replace(
    'result = fallback_plan(self.question, "planner_error:" + type(exc).__name__)',
    'result = comparison_fallback(self.question, "planner_error:" + type(exc).__name__)')
COMPLETE_RERANK_CODE=LOCAL_CODE.replace('class TextbookLocalReranker',PURE+'\nclass TextbookCompleteReranker')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('name = "TextbookLocalReranker"','name = "TextbookCompleteReranker"')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('display_name = "本地证据重排序 CrossEncoder"','display_name = "本地重排序与子问题覆盖"')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('rows = candidate_rows(self.candidates.to_dict(orient="records"))', '''raw_rows = self.candidates.to_dict(orient="records")
        retrieval_trace = raw_rows[0].get("retrieval_trace") if raw_rows else None
        if not retrieval_trace or retrieval_trace["plan"]["original_question"] != self.question:
            raise ValueError("检索计划与原问题不一致")
        queries = [json.dumps([q["query"],q["chapter"]],ensure_ascii=False) for q in retrieval_trace["plan"]["queries"]]
        rows = candidate_rows([{k:v for k,v in r.items() if k!="retrieval_trace"} for r in raw_rows])''')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('output = apply_local_scores(rows, scored["scores"], int(self.final_k))',
    'output = coverage_select(rows, scored["scores"], queries, int(self.final_k))')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('output = fallback_rows(rows, int(self.final_k), reason)',
    'output = coverage_select(rows, None, queries, int(self.final_k))')
COMPLETE_RERANK_CODE=COMPLETE_RERANK_CODE.replace('output[0]["rerank_trace"] = diagnostic','''diagnostic["queries"] = queries
        diagnostic["covered_queries"] = [q for q in queries if any(q in r["coverage_labels"] for r in output)]
        diagnostic["missing_queries"] = [q for q in queries if not any(q in r["coverage_labels"] for r in output)]
        diagnostic["retrieval_plan"] = retrieval_trace["plan"]
        output[0]["rerank_trace"] = diagnostic''')
