"""Score identical frozen 20-question pools locally; no model/API network calls."""
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from hybrid_retrieval import fuse_rrf, load_snapshot
from local_rerank_runtime import score_pairs
from rerank_retrieval import apply_local_scores

ROOT = Path(r'F:\daily\output\sysarch-rerank')
BASE = Path(r'F:\daily\output\sysarch-rag-evaluation\hybrid-verified-20261008')
DATASET = Path(r'F:\daily\output\sysarch-rag-evaluation\dataset.json')


def metrics(rows, gold):
    if not gold: return None
    ranks = [i for i, row in enumerate(rows, 1) if row['chunk_id'] in gold]
    dcg = sum(1/math.log2(i+1) for i in ranks)
    ideal = sum(1/math.log2(i+1) for i in range(1, min(5, len(gold))+1))
    return {'hit': bool(ranks), 'coverage': len(ranks)/len(gold),
            'mrr': 1/min(ranks) if ranks else 0, 'ndcg': dcg/ideal if ideal else 0}


def main():
    dest = ROOT/'candidate-replay'; dest.mkdir(exist_ok=True)
    setup = json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
    index = load_snapshot(setup['snapshot_path'], setup['snapshot_sha256'])
    tests = json.loads(DATASET.read_text(encoding='utf-8'))['tests']
    results = []
    for test in tests:
        path = dest/(test['id']+'.json')
        if path.exists():
            saved = json.loads(path.read_text(encoding='utf-8')); results.append(saved); continue
        basepath = BASE/(test['id']+'.json')
        recorded = json.loads(basepath.read_text(encoding='utf-8'))
        assert recorded['status'] == 'ok' and recorded['question'] == test['question']
        pool = fuse_rrf(recorded['dense_candidates'], recorded['lexical_candidates'], 20, 60)
        index.validate_candidates(pool)
        before = pool[:5]; start = time.perf_counter()
        scored = score_pairs(test['question'], pool)
        after = apply_local_scores(pool, scored['scores'], 5)
        elapsed = round(time.perf_counter()-start, 3)
        gold = {s['chunk_id'] for s in test['gold_sources']}
        result = {'id': test['id'], 'question': test['question'], 'source_record': str(basepath),
                  'source_record_sha256': hashlib.sha256(basepath.read_bytes()).hexdigest(),
                  'candidate_count': len(pool), 'candidates': pool, 'before': before, 'after': after,
                  'scores': scored, 'seconds': elapsed, 'before_metrics': metrics(before, gold),
                  'after_metrics': metrics(after, gold), 'reference_ids_in_pool': sorted(gold & {r['chunk_id'] for r in pool})}
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
        print(test['id'], elapsed, 'seconds', 'local', flush=True)
    summary = {'questions': len(results), 'offline_inference': True,
               'model': setup['model'], 'model_revision': setup['model_revision'],
               'cold_first_seconds': results[0]['seconds'],
               'warm_median_seconds': statistics.median(r['seconds'] for r in results[1:]),
               'warm_mean_seconds': statistics.mean(r['seconds'] for r in results[1:]),
               'changed_top5': sum([r['chunk_id'] for r in t['before']] != [r['chunk_id'] for r in t['after']] for t in results),
               'query_truncations': sum(bool(t['scores']['query_truncated']) for t in results)}
    for name in ('before', 'after'):
        values = [r[name+'_metrics'] for r in results if r[name+'_metrics'] is not None]
        summary[name] = {'answerable_count': len(values), 'hit': sum(v['hit'] for v in values),
                         'reference_id_coverage': statistics.mean(v['coverage'] for v in values),
                         'mrr': statistics.mean(v['mrr'] for v in values), 'ndcg_at5': statistics.mean(v['ndcg'] for v in values)}
    (dest/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__': main()
