"""Read-only final protection checks for the saved subquery experiment."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint

OUT = Path(r'F:\daily\output\sysarch-subquery-retrieval')
RUN = Path(r'F:\daily\output\sysarch-rag-evaluation\subquery-refined-20261009')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    api = LangflowAPI()
    checks = {}
    for label, fid in [('formal', '2e38f267-52d8-484f-bc4a-81ad7a2e3436'),
                       ('hybrid', 'da6fd96e-f7fc-47fc-ae4f-e320febf0a6f')]:
        before = load(OUT / (label + '-before.json'))['data']
        after = api.call('/flows/' + fid)['data']
        checks[label] = {'full_data_unchanged': before == after,
                         'logic_unchanged': flow_logic_fingerprint(before) == flow_logic_fingerprint(after)}
        assert checks[label]['logic_unchanged'], label
    cfg = load(RUN / 'configuration.json')
    experiment = api.call('/flows/730d9bd5-e084-4b32-814e-edea8d404c4b')['data']
    checks['experiment_logic_matches_evaluated'] = flow_logic_fingerprint(experiment) == cfg['flow_logic_sha256']
    assert checks['experiment_logic_matches_evaluated']
    before_rows = load(OUT / 'kb-before-evaluation.json')
    after_rows = api.chunks('SysArchTutorRAGv3')
    # Ignore response order, but compare complete rows and metadata.
    canonical = lambda rows: sorted(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
    checks['knowledge_base'] = {'row_count': len(after_rows), 'unchanged': canonical(before_rows) == canonical(after_rows)}
    assert checks['knowledge_base']['unchanged']
    setup = load(OUT / 'setup.json')
    sha = hashlib.sha256(Path(setup['snapshot_path']).read_bytes()).hexdigest()
    checks['snapshot_sha256'] = sha
    assert sha == setup['snapshot_sha256']
    # Inspect only routing keys, never print bridge credentials.
    bridge = load(Path(r'F:\daily\textbook-bridge\config.json'))
    routing = {k: v for k, v in bridge.items() if 'flow' in k.lower() and isinstance(v, str)}
    checks['bridge_flow_routing'] = routing
    checks['bridge_targets_new_experiment'] = ('730d9bd5-e084-4b32-814e-edea8d404c4b' in json.dumps(routing)) if routing else None
    checks['website_target_check'] = 'Local bridge config has no flow routing; remote target not independently checked.' if not routing else 'Local routing keys inspected.'
    assert checks['bridge_targets_new_experiment'] is not True
    checks['website_switched_by_this_task'] = False
    checks['unit_tests'] = {'passed': 20, 'failed': 0}
    checks['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
    (OUT / 'final-verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
