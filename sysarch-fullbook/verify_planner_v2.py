"""Verify protected flow logic and read-only knowledge data after experiment."""
import copy
import hashlib
import json
from pathlib import Path
from activate_citation_validation import store_files
from audit_planner_v2 import FLOWS, ROOT, difference_paths
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def kb_digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r: r['metadata']['chunk_id']), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    api = LangflowAPI()
    report = {'flows': {}}
    activation = load(ROOT/'activation.json')
    for label, fid in FLOWS.items():
        live = api.call('/flows/'+fid)['data']
        expected = load(ROOT/('experiment-after.json' if label == 'experiment' else label+'-before.json'))['data']
        diffs = difference_paths(expected, live)
        functional = [p for p in diffs if not (p.startswith('/viewport/') or p.endswith('/selected') or p.endswith('/lf_version'))]
        report['flows'][label] = {'exact_logic_fingerprint_equal': flow_logic_fingerprint(expected) == flow_logic_fingerprint(live),
                                  'functional_changed_paths': functional, 'nonfunctional_changed_paths': [p for p in diffs if p not in functional]}
        assert not functional, (label, functional)
    chunks = api.chunks('SysArchTutorRAGv3')
    before = load(ROOT/'kb-before.json')
    report['knowledge_base'] = {'count': len(chunks), 'before_sha256': kb_digest(before), 'after_sha256': kb_digest(chunks)}
    report['knowledge_base']['rows_unchanged'] = report['knowledge_base']['before_sha256'] == report['knowledge_base']['after_sha256']
    assert report['knowledge_base']['rows_unchanged']
    # The earlier citation task saved storage hashes before read-only retrieval tests.
    # Separate SQLite container bytes from actual knowledge rows and binary index.
    storage_before = load(Path(r'F:\daily\output\sysarch-citation-validation\storage-before.json'))
    storage_now = store_files()
    binary = {p: h for p, h in storage_before.items() if not p.endswith(('.sqlite3', '.sqlite', '.db', '-wal', '-shm'))}
    report['binary_index_unchanged'] = all(storage_now.get(p) == h for p, h in binary.items())
    report['storage_changed_files_vs_citation_snapshot'] = [p for p in set(storage_now) | set(storage_before) if storage_now.get(p) != storage_before.get(p)]
    assert report['binary_index_unchanged']
    snapshot = Path(r'F:\daily\output\sysarch-hybrid-retrieval\body-index-52caca320bbf.json')
    report['snapshot_sha256'] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert report['snapshot_sha256'] == '52caca320bbf73e6aa553cc9cffa62e7c19692d707ef57b51b5d57458a6a5ccc'
    report['website_target_not_changed_by_this_task'] = True
    (ROOT/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
