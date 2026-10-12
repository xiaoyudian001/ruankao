"""Create an independent Langflow hybrid experiment; never patch the source flow."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from hybrid_components import LEXICAL_CODE, FUSION_CODE
from hybrid_retrieval import BM25Index
from langflow_api import LangflowAPI

ROOT = Path(r"F:\daily\output\sysarch-hybrid-retrieval")
SOURCE_FLOW = "2e38f267-52d8-484f-bc4a-81ad7a2e3436"


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def edge(source, source_type, output, output_types, target, field, input_types, field_type):
    sh = {"id": source, "dataType": source_type, "name": output, "output_types": output_types}
    th = {"fieldName": field, "id": target, "inputTypes": input_types, "type": field_type}
    enc = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace('"', 'œ')
    a, b = enc(sh), enc(th)
    return {"animated": False, "className": "", "selected": False,
            "source": source, "target": target, "sourceHandle": a, "targetHandle": b,
            "data": {"sourceHandle": sh, "targetHandle": th},
            "id": "reactflow__edge-" + source + a + "-" + target + b}


def component(api, code, nid, position, values):
    compiled = api.call("/custom_component", {"code": code}, "POST")
    front = compiled["data"]
    front["template"]["code"]["value"] = code
    for key, value in values.items():
        front["template"][key]["value"] = value
    return {"id": nid, "type": "genericNode", "position": position, "selected": False,
            "data": {"id": nid, "type": compiled["type"], "node": front, "showNode": True,
                     "selected_output": front["outputs"][0]["name"]}}


def main():
    api = LangflowAPI()
    source = api.call("/flows/" + SOURCE_FLOW)
    saved = json.loads((ROOT / "source-flow.json").read_text(encoding="utf-8"))
    assert source["data"] == saved["data"], "Source flow changed during inspection"
    if (ROOT / "setup.json").exists():
        print((ROOT / "setup.json").read_text(encoding="utf-8"))
        return
    live = json.loads((ROOT / "kb-live-chunks.json").read_text(encoding="utf-8"))
    rows = [{**r["metadata"], "content": r["content"]} for r in live if r["metadata"].get("section_type") == "body"]
    rows.sort(key=lambda r: r["chunk_id"])
    assert len(rows) == len({r["chunk_id"] for r in rows}), "Duplicate chunk IDs"
    BM25Index(rows)
    snapshot = {"version": "sysarch-bm25-body-v1", "knowledge_base": "SysArchTutorRAGv3",
                "created_utc": datetime.now(timezone.utc).isoformat(), "count": len(rows),
                "tokenizer": "NFKC+Chinese-bigrams+ASCII-words-v1", "rows": rows}
    raw = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    path = ROOT / ("body-index-" + sha[:12] + ".json")
    path.write_bytes(raw)
    shared = {"snapshot_path": str(path), "snapshot_sha256": sha}
    lexical = component(api, LEXICAL_CODE, "TextbookBM25-SysArch", {"x": 100, "y": 380}, {**shared, "candidate_k": 20})
    fusion = component(api, FUSION_CODE, "TextbookRRF-SysArch", {"x": 600, "y": 720}, {**shared, "final_k": 5, "rrf_constant": 60})
    data = copy.deepcopy(source["data"])
    nodes = {n["id"]: n for n in data["nodes"]}
    reviewed_fields = json.loads(Path(r"F:\daily\output\sysarch-formula-fix\rollback-fields.json").read_text(encoding="utf-8"))["fields"]
    for reviewed in reviewed_fields:
        nodes[reviewed["node_id"]]["data"]["node"]["template"][reviewed["field"]]["value"] = reviewed["after"]
    nodes["Knowledge-Y8gm2"]["data"]["node"]["template"]["top_k"]["value"] = 20
    positions = {"ChatInput-z2rit": (100, 30), "Knowledge-Y8gm2": (600, 30), "parser-h3mx9": (1100, 720),
                 "Prompt Template-fzcHC": (1100, 1150), "LanguageModelComponent-BpTTF": (600, 1350),
                 "FinalAnswerCleaner-SysArch": (1100, 1720), "ChatOutput-QRg8s": (600, 1950)}
    for nid, (x, y) in positions.items():
        nodes[nid]["position"] = {"x": x, "y": y}
    data["nodes"] += [lexical, fusion]
    data["edges"] = [e for e in data["edges"] if not (e["source"] == "Knowledge-Y8gm2" and e["target"] == "parser-h3mx9")]
    lex_type = lexical["data"]["type"]
    fuse_type = fusion["data"]["type"]
    lex_types = lexical["data"]["node"]["outputs"][0]["types"]
    fuse_types = fusion["data"]["node"]["outputs"][0]["types"]
    data["edges"] += [
        edge("ChatInput-z2rit", "ChatInput", "message", ["Message"], lexical["id"], "query", ["Message"], "str"),
        edge("Knowledge-Y8gm2", "Knowledge", "retrieve_data", ["Table"], fusion["id"], "dense_candidates", ["DataFrame", "Table"], "other"),
        edge(lexical["id"], lex_type, "lexical_candidates", lex_types, fusion["id"], "lexical_candidates", ["DataFrame", "Table"], "other"),
        edge(fusion["id"], fuse_type, "fused_candidates", fuse_types, "parser-h3mx9", "input_data", ["DataFrame", "Table", "Data", "JSON"], "other"),
    ]
    # Retain downstream values exactly, even though canvas positions have changed.
    originals = {n["id"]: n for n in source["data"]["nodes"]}
    for nid, n in nodes.items():
        if nid != "Knowledge-Y8gm2":
            restored = copy.deepcopy(n["data"])
            for reviewed in reviewed_fields:
                if reviewed["node_id"] == nid:
                    restored["node"]["template"][reviewed["field"]]["value"] = originals[nid]["data"]["node"]["template"][reviewed["field"]]["value"]
            assert restored == originals[nid]["data"]
    data["viewport"] = {"x": 20, "y": 20, "zoom": .5}
    flow = api.call("/flows/", {"name": "教材检索与备考问答 · 混合检索实验",
                   "description": "同一正文语料：向量20＋BM25关键词20→RRF融合5；独立实验，不替换网页正式流程。",
                   "folder_id": source["folder_id"], "data": data}, "POST")
    returned = api.call("/flows/" + flow["id"])
    assert returned["data"] == data, "New flow differs after save"
    assert api.call("/flows/" + SOURCE_FLOW)["data"] == source["data"], "Original flow changed"
    (ROOT / "experiment-flow.json").write_text(json.dumps(returned, ensure_ascii=False, indent=2), encoding="utf-8")
    setup = {"flow_id": flow["id"], "flow_name": flow["name"], "source_flow_id": SOURCE_FLOW,
             "source_flow_sha256": digest(source["data"]), "experiment_flow_sha256": digest(data),
             "snapshot_path": str(path), "snapshot_sha256": sha, "body_chunks": len(rows),
             "dense_candidates": 20, "lexical_candidates": 20, "final_k": 5, "rrf_constant": 60,
             "lexical_node": lexical["id"], "fusion_node": fusion["id"], "source_flow_unchanged": True,
             "comparison_baseline": "formula-fix-20261008",
             "comparison_fields_restored": [r["node_id"] + "." + r["field"] for r in reviewed_fields],
             "website_switched": False}
    (ROOT / "setup.json").write_text(json.dumps(setup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(setup, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
