"""Normalize numbered citations from the exact rows supplied to the answer context.

This validates source identity/format, not whether a passage entails a claim.
"""
import re
import unicodedata

from citation_format import source_hint

_CODE = re.compile(r'```[^\n]*\n.*?```|~~~[^\n]*\n.*?~~~|`[^`\n]+`', re.S)
_CITATION = re.compile(r'[\[【［]\s*片段[^\]\n】］]*[\]】］]')
_RANKS = re.compile(r'片段\s*(\d+(?:\s*[、,，～~\-—–至到]\s*\d+)*)')
_NUMBER = re.compile(r'(\d+)(?:\s*([～~\-—–至到])\s*(\d+))?')
_PAGE = re.compile(r'(?:教材|(?:原)?PDF)\s*第?\s*\d+(?:\s*[～~\-—–、,，]\s*\d+)*\s*页', re.I)
_BARE_PAREN = re.compile(r'[（(]\s*(片段\s*\d+(?:\s*[、,，～~\-—–至到]\s*\d+)*)\s*[）)]')
_TABLE_SOURCE = re.compile(r'(?<=\|)([ \t]*)(片段\s*\d+(?:\s*[、,，～~\-—–至到]\s*\d+)*(?:[，,；;]\s*(?:教材|(?:原)?PDF|来源)[^\n|]*)?)[ \t]*(?=\|)', re.I)


def citation_label(rank, row):
    # Ignore any model/ranker-preformatted hint: reconstruct using mapped metadata.
    values = dict(row)
    values['source_file'] = ''
    values['chapter'] = re.sub(r'[\r\n\[\]【】［］]', ' ', str(values.get('chapter', ''))).strip()
    hint = source_hint(values)
    label = hint.partition('；')[2].replace('；', '，') if hint else ''
    return f'[片段{rank}，{label}]' if label else f'[片段{rank}]'


def _parse_ranks(payload):
    ranks = []
    for group in _RANKS.finditer(unicodedata.normalize('NFKC', payload)):
        for item in _NUMBER.finditer(group[1]):
            first, last = int(item[1]), int(item[3] or item[1])
            if last < first or last - first > 49:
                raise ValueError('Invalid citation range')
            ranks.extend(range(first, last + 1))
    if not ranks:
        raise ValueError('Missing citation rank')
    return list(dict.fromkeys(ranks))


def normalize_citations(text, rows):
    """Return normalized text plus diagnostics; rows must retain Parser order."""
    rows = list(rows)
    if len(rows) > 50 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Expected at most 50 source rows in context order')
    mapping = {i: citation_label(i, row) for i, row in enumerate(rows, 1)}
    referenced, invalid, malformed, unbound = [], [], [], []
    changed, count = 0, 0

    def replace(match):
        nonlocal changed, count
        original = match[0]
        count += 1
        try:
            ranks = _parse_ranks(original)
        except ValueError:
            malformed.append(original)
            changed += 1
            return '[引用未核验]'
        labels = []
        for rank in ranks:
            if rank not in mapping:
                invalid.append(rank)
                labels.append(f'[引用未核验：片段{rank}]')
            else:
                referenced.append(rank)
                labels.append(mapping[rank])
        result = ''.join(labels)
        changed += original != result
        return result

    def plain(segment):
        segment = _BARE_PAREN.sub(lambda m:'[' + m[1] + ']', segment)
        segment = _TABLE_SOURCE.sub(lambda m:m[1] + '[' + m[2].strip() + '] ', segment)
        # Detect free-standing page claims, but never guess their source binding.
        unbound.extend(_PAGE.findall(_CITATION.sub('', segment)))
        return _CITATION.sub(replace, segment)

    parts = []
    last = 0
    for code in _CODE.finditer(text):
        parts.extend([plain(text[last:code.start()]), code[0]])
        last = code.end()
    parts.append(plain(text[last:]))
    return {'text': ''.join(parts), 'referenced_ranks': list(dict.fromkeys(referenced)),
            'invalid_ranks': list(dict.fromkeys(invalid)), 'malformed_citations': malformed,
            'unbound_page_mentions': list(dict.fromkeys(unbound)),
            'citation_count': count, 'rewritten_count': changed}
