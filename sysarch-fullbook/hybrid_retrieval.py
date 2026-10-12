"""Source-preserving BM25 and reciprocal rank fusion for the local textbook."""
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

SNAPSHOT_ROOT = Path(r"F:\daily\output\sysarch-hybrid-retrieval").resolve()
SOURCE_KEYS = ("content", "source_sha256", "chunk_id", "pdf_pages", "book_pages")


def tokenize(text):
    text = unicodedata.normalize("NFKC", str(text)).lower()
    text = re.sub(r"(?<=[\u3400-\u9fff])[ \t]+(?=[\u3400-\u9fff])", "", text)
    terms = []
    for segment in re.findall(r"[\u3400-\u9fff]+|[a-z0-9]+(?:[._-][a-z0-9]+)*", text):
        if re.fullmatch(r"[\u3400-\u9fff]+", segment) and len(segment) > 1:
            terms.extend(segment[i:i + 2] for i in range(len(segment) - 1))
        else:
            terms.append(segment)
    return terms


def checked(row):
    row = dict(row)
    if not row.get("chunk_id") or not str(row.get("content", "")).strip():
        raise ValueError("候选缺少稳定分片ID或正文")
    if row.get("section_type") != "body":
        raise ValueError("混合检索仅允许正文分片")
    if not row.get("source_sha256") or not row.get("pdf_pages"):
        raise ValueError("候选缺少来源哈希或PDF页码")
    return row


def same_source(a, b):
    return all(str(a.get(key, "")) == str(b.get(key, "")) for key in SOURCE_KEYS)


def unique_rows(rows):
    result, seen = [], {}
    for item in rows:
        item = checked(item)
        key = item["chunk_id"]
        if key in seen:
            if not same_source(seen[key], item):
                raise ValueError("重复分片ID具有不同正文或来源：" + key)
            continue
        seen[key] = item
        result.append(item)
    return result


class BM25Index:
    def __init__(self, rows, k1=1.5, b=.75):
        self.rows = unique_rows(rows)
        if not self.rows:
            raise ValueError("关键词索引正文为空")
        self.by_id = {r["chunk_id"]: r for r in self.rows}
        self.k1, self.b = k1, b
        self.postings = defaultdict(list)
        self.lengths = []
        for i, row in enumerate(self.rows):
            # The chapter is indexed text, not a query-dependent boost or answer rule.
            terms = tokenize(row["content"] + "\n" + str(row.get("chapter", "")))
            self.lengths.append(len(terms))
            for term, frequency in Counter(terms).items():
                self.postings[term].append((i, frequency))
        self.avgdl = sum(self.lengths) / len(self.rows) or 1

    def search(self, query, limit=20):
        if not str(query).strip():
            raise ValueError("检索问题不能为空")
        if limit < 1:
            raise ValueError("候选数量必须为正")
        scores = defaultdict(float)
        n = len(self.rows)
        for term in sorted(set(tokenize(query))):
            posting = self.postings.get(term, ())
            if not posting:
                continue
            df = len(posting)
            idf = math.log(1 + (n - df + .5) / (df + .5))
            for i, frequency in posting:
                normalizer = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)
                scores[i] += idf * frequency * (self.k1 + 1) / (frequency + normalizer)
        ordered = sorted(scores, key=lambda i: (-scores[i], self.rows[i]["chunk_id"]))[:limit]
        return [{**self.rows[i], "bm25_score": scores[i], "lexical_rank": rank}
                for rank, i in enumerate(ordered, 1) if scores[i] > 0]

    def validate_candidates(self, rows):
        for row in unique_rows(rows):
            original = self.by_id.get(row["chunk_id"])
            if original is None or not same_source(original, row):
                raise ValueError("知识库与关键词快照不同步，请刷新索引：" + row["chunk_id"])


def fuse_rrf(dense, lexical, limit=5, constant=60):
    if limit < 1 or constant < 1:
        raise ValueError("最终片段数和RRF常数必须为正")
    merged = {}
    for route, candidates in (("dense", dense), ("lexical", lexical)):
        for rank, row in enumerate(unique_rows(candidates), 1):
            key = row["chunk_id"]
            if key not in merged:
                merged[key] = {**row, "dense_rank": None, "lexical_rank": None,
                               "bm25_score": None, "dense_score": None, "rrf_score": 0.}
            result = merged[key]
            if not same_source(result, row):
                raise ValueError("两路检索分片来源冲突：" + key)
            result[route + "_rank"] = rank
            if route == "dense":
                result["dense_score"] = row.get("_score")
            else:
                result["bm25_score"] = row.get("bm25_score")
            result["rrf_score"] += 1 / (constant + rank)
    ordered = sorted(merged.values(), key=lambda r: (-r["rrf_score"], min(r["dense_rank"] or math.inf, r["lexical_rank"] or math.inf), r["chunk_id"]))[:limit]
    return [{**r, "_score": r["rrf_score"], "retrieval_method": "bm25+dense+rrf"} for r in ordered]


@lru_cache(maxsize=2)
def _index_from_bytes(raw):
    data = json.loads(raw)
    if data.get("knowledge_base") != "SysArchTutorRAGv3":
        raise ValueError("关键词快照知识库名称不匹配")
    if data.get("count") != len(data["rows"]):
        raise ValueError("关键词快照分片数不匹配")
    return BM25Index(data["rows"])


def load_snapshot(path, expected_sha256):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(SNAPSHOT_ROOT) or resolved.suffix != ".json":
        raise ValueError("关键词索引必须位于教材混合检索目录")
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("关键词快照哈希变化，请重新确认索引版本")
    return _index_from_bytes(raw)
