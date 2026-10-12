"""Read-only flow audit; output paths and fingerprints, never parameter secrets."""
import copy
import json
from pathlib import Path
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint

ROOT = Path(r'F:\daily\output\sysarch-planner-v2')
FLOWS = {'formal': '2e38f267-52d8-484f-bc4a-81ad7a2e3436',
         'hybrid': 'da6fd96e-f7fc-47fc-ae4f-e320febf0a6f',
         'experiment': '730d9bd5-e084-4b32-814e-edea8d404c4b'}


def difference_paths(a, b, prefix=''):
    if isinstance(a, dict) and isinstance(b, dict):
        return [p for k in sorted(set(a) | set(b)) for p in
                ([prefix+'/'+k] if k not in a or k not in b else difference_paths(a[k], b[k], prefix+'/'+k))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in difference_paths(x, y, prefix+'/'+str(i))]
    return [] if a == b else [prefix]


def main():
    api = LangflowAPI()
    report = {}
    for label, fid in FLOWS.items():
        current = api.call('/flows/'+fid)
        (ROOT/(label+'-audit-current.json')).write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
        old = json.loads((ROOT/(label+'-before.json')).read_text(encoding='utf-8'))
        report[label] = {'logic_unchanged': flow_logic_fingerprint(old['data']) == flow_logic_fingerprint(current['data']),
                         'changed_paths': difference_paths(old['data'], current['data'])}
        if label == 'experiment':
            baseline = json.loads(Path(r'F:\daily\output\sysarch-rag-evaluation\planner-v1-citation-baseline-20261009\evaluated-flow.json').read_text(encoding='utf-8'))
            report[label]['baseline_changed_paths'] = difference_paths(baseline, current['data'])
    (ROOT/'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
