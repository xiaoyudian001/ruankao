"""Source for two self-contained Langflow components, compiled individually."""
from pathlib import Path

COMMON = Path(__file__).with_name("hybrid_retrieval.py").read_text(encoding="utf-8") + '''
from lfx.custom import Component
from lfx.io import StrInput, MessageTextInput, HandleInput, IntInput, Output
from lfx.schema.dataframe import DataFrame

'''

LEXICAL_CODE = COMMON + '''class TextbookBM25(Component):
    display_name = "关键词检索 BM25"
    description = "从固定版本的正文索引匹配中文二字片段与英文术语，保留原页码。"
    icon = "Search"
    name = "TextbookBM25"
    inputs = [
        MessageTextInput(name="query", display_name="检索问题", required=True),
        StrInput(name="snapshot_path", display_name="正文索引路径", required=True, advanced=True),
        StrInput(name="snapshot_sha256", display_name="索引版本SHA256", required=True, advanced=True),
        IntInput(name="candidate_k", display_name="关键词候选数", value=20),
    ]
    outputs = [Output(name="lexical_candidates", display_name="关键词候选", method="search")]

    def search(self) -> DataFrame:
        index = load_snapshot(self.snapshot_path, self.snapshot_sha256)
        rows = index.search(self.query, int(self.candidate_k))
        self.status = f"正文{len(index.rows)}片；关键词候选{len(rows)}片；BM25 k1=1.5 b=0.75"
        if not rows:
            return DataFrame({"chunk_id": [], "content": [], "bm25_score": []})
        return DataFrame(rows)
'''

FUSION_CODE = COMMON + '''class TextbookRRF(Component):
    display_name = "融合排序 RRF"
    description = "融合关键词与语义排名，按分片ID去重。保留各路排名和来源，分数不是概率。"
    icon = "Merge"
    name = "TextbookRRF"
    inputs = [
        HandleInput(name="dense_candidates", display_name="语义候选", input_types=["DataFrame", "Table"], required=True),
        HandleInput(name="lexical_candidates", display_name="关键词候选", input_types=["DataFrame", "Table"], required=True),
        StrInput(name="snapshot_path", display_name="正文索引路径", required=True, advanced=True),
        StrInput(name="snapshot_sha256", display_name="索引版本SHA256", required=True, advanced=True),
        IntInput(name="final_k", display_name="最终片段数", value=5),
        IntInput(name="rrf_constant", display_name="RRF常数", value=60, advanced=True),
    ]
    outputs = [Output(name="fused_candidates", display_name="融合后的教材片段", method="fuse")]

    def fuse(self) -> DataFrame:
        dense = self.dense_candidates.to_dict(orient="records")
        lexical = self.lexical_candidates.to_dict(orient="records")
        index = load_snapshot(self.snapshot_path, self.snapshot_sha256)
        index.validate_candidates(dense)
        index.validate_candidates(lexical)
        rows = fuse_rrf(dense, lexical, int(self.final_k), int(self.rrf_constant))
        self.status = f"语义{len(dense)}＋关键词{len(lexical)}→融合{len(rows)}片；RRF常数{self.rrf_constant}"
        return DataFrame(rows)
'''
