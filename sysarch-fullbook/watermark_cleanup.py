"""Remove only watermark OCR lines verified against the original PDF pages."""

import hashlib
import json
import re
from pathlib import Path

from core import save_json_atomic

VERSION = 'sysarch-v3-watermark-1'


# These are OCR artifacts from the diagonal "淘宝搜索：文老师系统架构设计师"
# watermark, checked against a render of the named physical PDF pages.
REMOVE_LINES = {
    1: {'宝搜'},
    2: {'淘宝搜', '淘宝搜索', '设计师'},
    5: {'淘宝搜索：文老师系统架构设计师'},
    15: {'淘宝搜索：文老师系统架构设计师'},
    16: {'文老师系统架构设计师', '淘宝搜索：', '淘宝搜索',
         '淘宝搜索：文老师系统架构设计师文老师系统架构设计师',
         '淘宝搜索淘宝搜索：文老师系统架构设计师'},
    17: {'淘宝搜索：文老师系统架构设计师'},
    38: {'文老师系', '淘宝搜索：', '文老师系统架构设计师', '宝搜索：'},
    119: {'淘宝搜索：文老', '宝搜索：文老师系统架构设计师'},
    189: {'淘宝搜索：文老师系', '宝搜索：文老师系统架构设计师', '架构设计'},
    418: {'：文老师系统架构设计师', '淘宝搜索：'},
    419: {'淘宝搜索：文老师系统架构设计师'},
    647: {'淘宝', '宝搜索：文老师系统架构设计'},
}

REPLACE_LINES = {
    16: {'上篇文老师系统架构设计师': '上篇'},
    418: {'下篇淘宝搜索：文老师系统架构设计师': '下篇',
          '下篇淘宝搜索：文老师系统架构设计师淘宝搜索：文老师系统架构设计师': '下篇'},
}


def clean_markdown(page, markdown):
    removals = REMOVE_LINES.get(page, set())
    replacements = REPLACE_LINES.get(page, {})
    if not removals and not replacements:
        return markdown
    output = []
    changed = False
    for line in markdown.split('\n'):
        stripped = line.strip()
        if stripped in removals:
            changed = True
            continue
        if stripped in replacements:
            output.append(replacements[stripped])
            changed = True
        else:
            output.append(line)
    if not changed:
        return markdown
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(output)).strip()


def clean_stored_chunk(row):
    content = row['content']
    pages = [int(page) for page in row['metadata']['pdf_pages'].split(',')]
    for page in pages:
        content = clean_markdown(page, content)
    return content


def build_corpus(source_root, target_root):
    source_root, target_root = Path(source_root).resolve(), Path(target_root).resolve()
    if source_root == target_root or source_root in target_root.parents:
        raise ValueError('The derived corpus must be outside the V2 source directory.')
    target_pages = target_root / 'pages'
    target_pages.mkdir(parents=True, exist_ok=True)
    page_paths = [path for path in sorted((source_root / 'pages').glob('page_*.md'))
                  if re.fullmatch(r'page_\d{4}\.md', path.name)]
    changed_pages = []
    for path in page_paths:
        page = int(path.stem.split('_')[1])
        original = path.read_text(encoding='utf-8')
        cleaned = clean_markdown(page, original)
        (target_pages / path.name).write_text(cleaned, encoding='utf-8')
        if cleaned != original:
            changed_pages.append(page)

    source_chunks = json.loads((source_root / 'final_chunks.json').read_text(encoding='utf-8'))
    derived_chunks = []
    ingest_rows = []
    changes = []
    for source in source_chunks:
        content = clean_stored_chunk(source)
        if not content.strip():
            raise ValueError('Cleanup would erase a whole stored chunk: ' + source['id'])
        metadata = dict(source['metadata'])
        old_chunk_id = metadata['chunk_id']
        chunk_id = hashlib.sha256((VERSION + '|' + old_chunk_id + '|' + content).encode('utf-8')).hexdigest()
        metadata['chunk_id'] = chunk_id
        metadata['_id'] = hashlib.sha256((VERSION + '|' + source['id']).encode('utf-8')).hexdigest()
        metadata['processing_version'] = VERSION
        source_metadata = json.loads(metadata.get('source_metadata') or '{}')
        source_metadata['chunk_id'] = chunk_id
        metadata['source_metadata'] = json.dumps(source_metadata, ensure_ascii=False)
        derived_chunks.append({'id': source['id'], 'content': content,
                               'char_count': len(content), 'metadata': metadata})
        row = {'text': content, **{key: value for key, value in metadata.items()
                                   if key not in {'_id', 'source_metadata'}},
               'source_metadata': metadata['source_metadata']}
        row['pdf_page_start'] = int(row['pdf_page_start'])
        row['pdf_page_end'] = int(row['pdf_page_end'])
        ingest_rows.append(row)
        if content != source['content']:
            changes.append({'id': source['id'], 'pdf_pages': metadata['pdf_pages'],
                            'old_chunk_id': old_chunk_id, 'new_chunk_id': chunk_id,
                            'old_length': len(source['content']), 'new_length': len(content)})

    save_json_atomic(target_root / 'final_chunks.json', derived_chunks)
    save_json_atomic(target_root / 'ingest_rows.json', ingest_rows)
    report = {'source': str(source_root), 'target': str(target_root), 'version': VERSION,
              'pages': len(page_paths),
              'chunks': len(derived_chunks), 'changed_pages': changed_pages,
              'changed_chunks': len(changes), 'chunk_changes': changes}
    save_json_atomic(target_root / 'cleanup_report.json', report)
    return report


if __name__ == '__main__':
    source = Path(r'F:\daily\output\sysarch-fullbook-v2')
    target = Path(r'F:\daily\output\sysarch-fullbook-v3-watermark')
    print(json.dumps(build_corpus(source, target), ensure_ascii=False))
