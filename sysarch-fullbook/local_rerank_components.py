"""Offline reranker source for Langflow; no remote language-model input."""
from pathlib import Path

HERE = Path(__file__).parent
PURE = (HERE/'hybrid_retrieval.py').read_text(encoding='utf-8') + '\n' + (HERE/'rerank_retrieval.py').read_text(encoding='utf-8').replace('from hybrid_retrieval import unique_rows', '')

LOCAL_CODE = PURE + '''
import asyncio
import time
import sys
import importlib.util
import threading
from lfx.custom import Component
from lfx.io import MessageTextInput, HandleInput, IntInput, StrInput, Output
from lfx.schema.dataframe import DataFrame

class TextbookLocalReranker(Component):
    display_name = "本地证据重排序 CrossEncoder"
    description = "原问题与RRF前20片在本机成对评分，窗口覆盖原文，选5片；失败回退RRF，分数非概率。"
    icon = "ListFilter"
    name = "TextbookLocalReranker"
    inputs = [
        MessageTextInput(name="question", display_name="原问题", required=True),
        HandleInput(name="candidates", display_name="RRF候选", input_types=["DataFrame", "Table"], required=True),
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
        index.validate_candidates(rows)
        if not rows:
            self.status = "无候选，不运行本地模型"
            return DataFrame({"content": [], "chunk_id": [], "rag_rank": []})
        diagnostic = {"candidate_count": len(rows), "final_k": int(self.final_k), "input_ids": [r["chunk_id"] for r in rows],
                      "engine": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", "network_used": False}
        try:
            key = '_sysarch_local_rerank_v1'
            if key not in sys.modules:
                spec = importlib.util.spec_from_file_location(key, r'F:\\daily\\sysarch-fullbook\\local_rerank_runtime.py')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Multiple graphs in the same process share the loaded model and inference lock.
                sys.modules.setdefault(key, module)
            runtime = sys.modules[key]
            scored = await asyncio.wait_for(asyncio.to_thread(runtime.score_pairs, self.question, rows), timeout=90)
            output = apply_local_scores(rows, scored["scores"], int(self.final_k))
            diagnostic.update(scored)
            diagnostic["route"] = "reranked"
        except Exception as exc:
            reason = type(exc).__name__
            output = fallback_rows(rows, int(self.final_k), reason)
            diagnostic.update({"route": "rrf_fallback", "fallback_type": reason})
        diagnostic.update({"seconds": round(time.perf_counter()-start, 3), "output_ids": [r["chunk_id"] for r in output]})
        self.status = json.dumps(diagnostic, ensure_ascii=False)
        output[0]["rerank_trace"] = diagnostic
        return DataFrame(output)
'''
