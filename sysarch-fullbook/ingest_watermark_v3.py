"""Resume verified ingestion of the watermarked-page cleanup into a separate KB."""

import json
import time
from pathlib import Path

from core import save_json_atomic
from langflow_api import LangflowAPI


V2_ROOT = Path(r'F:\daily\output\sysarch-fullbook-v2')
V3_ROOT = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')
BATCH_ROOT = V2_ROOT / 'clean_v3_ingest'  # Required by the existing batch-reader sandbox.
FLOW_ID = '7b965a0c-d610-42b0-a986-8557aadb207a'
KB = 'SysArchTutorRAGv3'


def verify_rows(api, rows):
    stored = {item['metadata'].get('chunk_id'): item
              for item in api.chunks(KB, [row['chunk_id'] for row in rows])}
    if not all(row['chunk_id'] in stored for row in rows):
        return False
    for row in rows:
        actual = stored[row['chunk_id']]
        assert actual['content'] == row['text'], 'Stored text differs: ' + row['chunk_id']
        assert actual['metadata']['pdf_pages'] == row['pdf_pages']
        assert actual['metadata']['chapter'] == row['chapter']
        assert actual['metadata']['processing_version'] == row['processing_version']
    return True


def ingest():
    api = LangflowAPI()
    assert api.call('/knowledge_bases/SysArchTutorRAGv2')['chunks'] == 1675
    config = api.call('/knowledge_bases/' + KB)
    assert config['embedding_provider'] == 'Ollama'
    assert config['embedding_model'] == 'bge-m3:latest'
    assert config['backend_type'] == 'chroma'
    batches = sorted(BATCH_ROOT.glob('batch_*.json'))
    assert len(batches) == 34
    for index, path in enumerate(batches, 1):
        rows = json.loads(path.read_text(encoding='utf-8'))
        assert 0 < len(rows) <= 50
        if not verify_rows(api, rows):
            last_error = None
            for attempt in range(3):
                try:
                    api.run_ingest(FLOW_ID, path, kb=KB)
                    assert verify_rows(api, rows), 'Batch incomplete after ingestion'
                    last_error = None
                    break
                except Exception as error:
                    last_error = error
                    print('RETRY', index, attempt + 1, str(error)[:350], flush=True)
                    if attempt < 2:
                        time.sleep(3)
            if last_error:
                raise last_error
        save_json_atomic(V3_ROOT / 'ingest_progress.json',
                         {'completed_batches': index, 'total_batches': len(batches),
                          'verified_rows_through_batch': min(index * 50, 1675),
                          'knowledge_base': KB})
        print('VERIFIED', index, len(batches), 'rows', len(rows), flush=True)

    expected = json.loads((V3_ROOT / 'final_chunks.json').read_text(encoding='utf-8'))
    actual = api.chunks(KB)
    assert len(actual) == len(expected) == 1675
    by_id = {item['metadata']['chunk_id']: item for item in actual}
    assert len(by_id) == len(actual)
    for row in expected:
        item = by_id[row['metadata']['chunk_id']]
        assert item['content'] == row['content']
        assert item['metadata']['pdf_pages'] == row['metadata']['pdf_pages']
    assert api.call('/knowledge_bases/SysArchTutorRAGv2')['chunks'] == 1675
    save_json_atomic(V3_ROOT / 'ingest_verification.json',
                     {'knowledge_base': KB, 'verified_chunks': len(actual),
                      'v2_chunks_preserved': 1675, 'all_text_and_page_metadata_match': True})
    print('V3_INGEST_COMPLETE', len(actual), flush=True)


if __name__ == '__main__':
    ingest()
