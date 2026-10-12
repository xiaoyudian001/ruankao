"""Exercise the saved final cleaners with real retrieval metadata, without an LLM call."""
import json
from pathlib import Path

from activate_source_references import FLOWS
from langflow_api import LangflowAPI
from lfx.schema.message import Message
from lfx.schema.dataframe import DataFrame


def main():
    fixture = json.loads(Path(r'F:\daily\output\sysarch-citation-viewer\flow-verification.json').read_text(encoding='utf-8'))['references'][0]
    row = {'source_sha256': fixture['bookSha'], 'chunk_id': fixture['chunkId'],
           'content': fixture['content'], 'pdf_page_start': fixture['pdfPages'][0],
           'pdf_page_end': fixture['pdfPages'][-1], 'chapter': fixture['chapter']}
    api = LangflowAPI()
    failures = []
    for label, fid in FLOWS.items():
        flow = api.call('/flows/'+fid)
        node = next(n for n in flow['data']['nodes'] if n['id']=='FinalAnswerCleaner-SysArch')
        scope = {}
        exec(compile(node['data']['node']['template']['code']['value'], '<saved-cleaner>', 'exec'), scope)
        cleaner = scope['FinalAnswerCleaner'](_code=node['data']['node']['template']['code']['value'])
        cleaner.set(input_message=Message(text='教材定义。[片段1]'), reference_data=DataFrame([row]))
        output = cleaner.clean_message()
        refs = (output.session_metadata or {}).get('textbook_refs', [])
        valid = len(refs)==1 and refs[0]['chunkId']==fixture['chunkId'] and refs[0]['pdfPages']==fixture['pdfPages'] and refs[0]['content']==fixture['content']
        print(json.dumps({'flow':label,'snapshot_count':len(refs),'passed':valid},ensure_ascii=False))
        if not valid:
            failures.append(label)
    assert not failures, 'Actual saved cleaners lost source snapshots: '+', '.join(failures)


if __name__=='__main__':
    main()
