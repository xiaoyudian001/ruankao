"""Offline-only multilingual CrossEncoder; cached once in the Langflow process."""
import json
import threading
from functools import lru_cache
from pathlib import Path

MODEL_DIR = Path(r'F:\daily\models\mmarco-mMiniLMv2-L12-H384-v1')
MODEL_REVISION = '1427fd652930e4ba29e8149678df786c240d8825'
LOCK = threading.Lock()


@lru_cache(maxsize=1)
def load_model():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    manifest = json.loads((MODEL_DIR/'download-manifest.json').read_text(encoding='utf-8'))
    if manifest != {'repo': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1', 'revision': MODEL_REVISION}:
        raise ValueError('Local model revision differs from reviewed download')
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True,
              trust_remote_code=False, use_safetensors=True).to('cpu').eval()
    if model.config.model_type != 'xlm-roberta':
        raise ValueError('Expected the reviewed XLM-RoBERTa pair template')
    return tokenizer, model


def score_pairs(question, rows):
    import torch
    if not str(question).strip() or len(str(question)) > 4000 or len(rows) > 20:
        raise ValueError('Invalid local reranking batch')
    with LOCK:
        tokenizer, model = load_model()
        # Limit oversubscription while holding the inference lock. Restore the host setting.
        previous_threads = torch.get_num_threads()
        torch.set_num_threads(min(previous_threads, 4))
        try:
            full_query = tokenizer.encode(question, add_special_tokens=False)
            query = full_query[:128]
            windows, owners, counts = [], [], []
            special = tokenizer.num_special_tokens_to_add(pair=True)
            width = 512-len(query)-special
            for i, row in enumerate(rows):
                document = tokenizer.encode(row['content'], add_special_tokens=False)
                count = 0
                for offset in range(0, max(1, len(document)), width-64):
                    window = document[offset:offset+width]
                    # XLM-R pair template: <s>A</s></s>B</s>. Transformers 5 removed
                    # prepare_for_model; constructing IDs also avoids lossy token decoding.
                    ids = [tokenizer.bos_token_id]+query+[tokenizer.sep_token_id]*2+window+[tokenizer.sep_token_id]
                    features = {'input_ids': ids, 'attention_mask': [1]*len(ids)}
                    windows.append(features); owners.append(i); count += 1
                    if offset+width >= len(document): break
                counts.append(count)
            scores = [float('-inf')]*len(rows)
            with torch.inference_mode():
                for start in range(0, len(windows), 4):
                    batch = tokenizer.pad(windows[start:start+4], padding=True, return_tensors='pt')
                    values = model(**batch).logits.reshape(-1).tolist()
                    if len(values) != len(windows[start:start+4]):
                        raise ValueError('Unexpected classifier output shape')
                    for j, value in enumerate(values):
                        owner = owners[start+j]; scores[owner] = max(scores[owner], float(value))
            return {'scores': scores, 'window_counts': counts, 'model_revision': MODEL_REVISION,
                    'query_token_count': len(full_query), 'query_truncated': len(full_query)>128,
                    'document_strategy': 'max-logit-over-overlapping-full-document-windows',
                    'device': 'cpu', 'network_used': False}
        finally:
            torch.set_num_threads(previous_threads)
