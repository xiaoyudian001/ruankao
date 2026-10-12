"""Self-contained source for the actual Langflow reranker node."""
from pathlib import Path

HERE = Path(__file__).parent
PURE = (HERE/'hybrid_retrieval.py').read_text(encoding='utf-8') + '\n' + (HERE/'rerank_retrieval.py').read_text(encoding='utf-8').replace('from hybrid_retrieval import unique_rows', '')

RERANK_CODE = PURE + '''
import asyncio
import time
from langchain_core.messages import SystemMessage, HumanMessage
from lfx.custom import Component
from lfx.io import MessageTextInput, HandleInput, IntInput, StrInput, Output
from lfx.schema.dataframe import DataFrame

class TextbookReranker(Component):
    display_name = "证据相关性重排序"
    description = "原问题与RRF前20片一次评分，保留原文/页码，选5片；失败回退RRF。分数非概率。"
    icon = "ListFilter"
    name = "TextbookReranker"
    inputs = [
        MessageTextInput(name="question", display_name="原问题", required=True),
        HandleInput(name="candidates", display_name="RRF候选", input_types=["DataFrame", "Table"], required=True),
        HandleInput(name="rerank_model", display_name="相关性评分模型", input_types=["LanguageModel"], required=True),
        IntInput(name="final_k", display_name="最终片段数", value=5),
        StrInput(name="snapshot_path", display_name="正文索引路径", required=True, advanced=True),
        StrInput(name="snapshot_sha256", display_name="索引SHA256", required=True, advanced=True),
    ]
    outputs = [Output(name="reranked_candidates", display_name="重排后的教材片段", method="rerank")]

    async def rerank(self) -> DataFrame:
        start = time.perf_counter()
        rows = candidate_rows(self.candidates.to_dict(orient="records"))
        final_limit(int(self.final_k))
        index = load_snapshot(self.snapshot_path, self.snapshot_sha256)
        # Source mismatch is fatal, not an acceptable scoring fallback.
        index.validate_candidates(rows)
        if not rows:
            self.status = "无候选，不调用评分模型"
            return DataFrame({"content": [], "chunk_id": [], "rag_rank": []})
        called = False
        diagnostic = {"candidate_count": len(rows), "final_k": int(self.final_k), "input_ids": [r["chunk_id"] for r in rows]}
        try:
            payload = make_payload(self.question, rows)
            called = True
            answer = await asyncio.wait_for(self.rerank_model.ainvoke([
                SystemMessage(content=RERANK_SYSTEM), HumanMessage(content=payload)]), timeout=60)
            output = apply_scores(rows, answer.content, int(self.final_k))
            diagnostic["scores"] = sorted(decode_scores(answer.content), key=lambda s: s["id"])
            diagnostic["route"] = "reranked"
        except Exception as exc:
            reason = type(exc).__name__
            output = fallback_rows(rows, int(self.final_k), reason)
            diagnostic.update({"route": "rrf_fallback", "fallback_type": reason})
        diagnostic.update({"model_called": called, "seconds": round(time.perf_counter()-start, 3),
                           "output_ids": [r["chunk_id"] for r in output]})
        self.status = json.dumps(diagnostic, ensure_ascii=False)
        output[0]["rerank_trace"] = diagnostic
        return DataFrame(output)
'''
