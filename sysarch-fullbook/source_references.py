"""Snapshot actual ordered retrieval rows; never reconstruct citations by searching again."""
from citation_format import source_hint
BOOK_SHA = 'edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'


def source_references(rows):
    refs = []
    for rank, row in enumerate(rows[:10], 1):
        if row.get('source_sha256') != BOOK_SHA:
            continue
        try:
            first, last = int(row['pdf_page_start']), int(row['pdf_page_end'])
        except (KeyError, TypeError, ValueError):
            continue
        if not 1 <= first <= last <= 728 or last-first > 5:
            continue
        label = source_hint(row).split('；', 1)[-1]
        content = row.get('content', '')
        if not isinstance(content, str) or not content.strip():
            continue
        refs.append({'rank': rank, 'bookSha': BOOK_SHA, 'chunkId': str(row.get('chunk_id', '')),
                     'content': content[:12000], 'pdfPages': list(range(first, last+1)),
                     'label': label[:500], 'chapter': str(row.get('chapter', ''))[:200]})
    return refs
