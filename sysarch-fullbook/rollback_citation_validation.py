"""Manually restore this task's three flow snapshots after guarding newer logic edits."""
from activate_citation_validation import ROOT, FLOWS, load
from langflow_api import LangflowAPI
from run_rag_evaluation import flow_logic_fingerprint


def main():
    api=LangflowAPI();manifest=load(ROOT/'activation.json')
    live={label:api.call('/flows/'+fid)['data'] for label,fid in FLOWS.items()}
    for label,data in live.items():
        assert flow_logic_fingerprint(data)==manifest['flows'][label]['after_logic_sha256'], 'Newer changes exist; do not overwrite'
    for label,fid in FLOWS.items():
        before=load(ROOT/'backups'/(label+'-before.json'))['data']
        api.call('/flows/'+fid,{'data':before},'PATCH')
        assert api.call('/flows/'+fid)['data']==before
    print('Restored the three pre-validation flow snapshots; knowledge store untouched.')


if __name__=='__main__':main()
