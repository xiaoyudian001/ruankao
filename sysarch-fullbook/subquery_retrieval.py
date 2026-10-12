"""Pure query planning constraints and source-preserving evidence merge."""
import json
import re
import unicodedata
from hybrid_retrieval import same_source, unique_rows


def chapter_number(value):
    value = unicodedata.normalize('NFKC', str(value))
    if value.isdigit():
        return int(value)
    digits = dict(zip('零一二三四五六七八九', range(10)))
    digits['两'] = 2
    if '十' in value:
        a, b = value.split('十', 1)
        return (digits.get(a, 1) if a else 1) * 10 + (digits.get(b, 0) if b else 0)
    return digits.get(value, 0)


def explicit_chapters(question):
    text = unicodedata.normalize('NFKC', str(question))
    values = [chapter_number(m) for m in re.findall(r'第\s*([0-9零一二三四五六七八九十两]+)\s*章', text)]
    return list(dict.fromkeys(v for v in values if v > 0))


def needs_split(question):
    if not str(question).strip():
        raise ValueError('问题不能为空')
    return len(explicit_chapters(question)) > 1 or len(re.findall(r'[?？]',question)) >= 3 or bool(re.search(r'比较|区别|不同|结合|分别.*(?:定义|解释)|侧重点', question))


def fallback_plan(question, reason='direct'):
    if not str(question).strip():
        raise ValueError('问题不能为空')
    chapters = explicit_chapters(question)
    if len(chapters) > 3:
        raise ValueError('当前实验一次最多处理3个显式章节，请缩小范围')
    queries = [{'query': question.strip(), 'chapter': n} for n in chapters] if chapters else [{'query': question.strip(), 'chapter': None}]
    return {'original_question': question, 'route': 'scoped_fallback' if len(queries) > 1 else 'direct',
            'reason': reason, 'queries': queries}


def decode_plan(raw):
    """Decode search-plan JSON without retaining a model's thinking text."""
    if isinstance(raw, list):
        raw = ''.join(p.get('text', '') if isinstance(p, dict) else str(p) for p in raw)
    text = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', str(raw), flags=re.S | re.I).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I).strip()
    return json.loads(text)


def safe_plan_diagnostic(raw):
    """Keep only bounded search fields from JSON, never raw response or thinking."""
    try:
        data = decode_plan(raw)
    except (ValueError, TypeError):
        return {'decoded': False}
    if not isinstance(data, dict) or not isinstance(data.get('queries'), list):
        return {'decoded': True, 'valid_shape': False}
    rows = []
    for item in data['queries'][:3]:
        if not isinstance(item, dict):
            rows.append({'invalid_entry': True})
            continue
        query, chapter = item.get('query'), item.get('chapter')
        # Do not store nested data, extra fields, or a raw response on schema failure.
        rows.append({'query': query[:400] if isinstance(query, str) else None,
                     'chapter': chapter[:40] if isinstance(chapter, str) else chapter
                         if chapter is None or type(chapter) in (int, float, bool) else None})
    return {'decoded': True, 'query_count': len(data['queries']), 'queries': rows}


def english_terms(text):
    # Python's Unicode \\b treats Chinese and ASCII letters as the same word.
    # Use ASCII identifier boundaries so 中文MTTR中文 and 中文Kafka both match.
    normalized = unicodedata.normalize('NFKC', str(text))
    return re.findall(r'(?<![A-Za-z0-9_-])[A-Za-z][A-Za-z0-9_-]*(?![A-Za-z0-9_-])', normalized)


# Match whole question phrases, rather than granting their individual characters.
_GENERIC_PHRASES = sorted(('是什么', '如何', '有哪些', '为什么', '分别', '请', '说明',
    '定义', '含义', '组成', '条件', '原因', '影响', '因素', '解释', '教材', '中',
    '根据', '及', '与', '的', '和', '区别', '比较', '不同', '各自', '职责', '划分',
    '描述', '重点', '关注', '关系', '内容', '方面', '意义', '作用', '特征', '改进',
    '视角', '除此之外', '除了', '之外', '还有', '关于', '相关', '知识点', '从',
    '在', '哪些', '什么', '为何', '怎样', '是否', '能否', '以及'), key=len, reverse=True)


def normalize_plan_chapter(value, chapters, repairs, entry_index):
    if value is None and len(chapters) == 1:
        repairs.append({'entry': entry_index, 'kind': 'single_chapter_from_question', 'chapter': chapters[0]})
        return chapters[0]
    if value is None:
        if chapters:
            raise ValueError('已指定章节，子问题必须携带章节范围')
        return None
    chapter = value
    if isinstance(value, str):
        label = unicodedata.normalize('NFKC', value).strip()
        if re.fullmatch(r'[0-9]+', label):
            chapter = int(label)
        elif re.fullmatch(r'第\s*[0-9零一二三四五六七八九十两]+\s*章', label):
            numbers = explicit_chapters(label)
            chapter = numbers[0] if len(numbers) == 1 else None
        else:
            raise ValueError('章节字段不是明确的章节编号')
        if type(chapter) is int and chapter in chapters:
            repairs.append({'entry': entry_index, 'kind': 'chapter_format', 'chapter': chapter})
    if type(chapter) is not int or chapter not in chapters:
        raise ValueError('禁止模型添加用户未指定的章节')
    return chapter


def parse_plan(question, raw):
    data = decode_plan(raw)
    if not isinstance(data, dict) or set(data) != {'queries'}:
        raise ValueError('计划必须是仅包含queries的JSON对象')
    entries = data['queries']
    if not isinstance(entries, list) or not 2 <= len(entries) <= 3:
        raise ValueError('拆分计划必须有2至3条')
    chapters = explicit_chapters(question)
    seen, queries, repairs = set(), [], []
    for entry_index, item in enumerate(entries):
        if not isinstance(item, dict) or 'query' not in item or set(item) - {'query', 'chapter'}:
            raise ValueError('每条计划只允许query和chapter')
        query = item['query']
        chapter = normalize_plan_chapter(item.get('chapter'), chapters, repairs, entry_index)
        if not isinstance(query, str) or not query.strip() or len(query) > 400:
            raise ValueError('子问题为空或过长')
        # Conservative extractive planning: forbid adding unasked substantive terms.
        # This is a character-level guard, not a guarantee of semantic equivalence.
        phrases = list(_GENERIC_PHRASES)
        if re.search(r'转成|转为|转化|转换|转变', question):
            phrases.extend(['转换', '将'])
        check_text = unicodedata.normalize('NFKC', query)
        check_text = re.sub('|'.join(re.escape(p) for p in sorted(phrases, key=len, reverse=True)), '', check_text)
        added = set(re.findall(r'[\u3400-\u9fff]', check_text)) - set(question)
        if added:
            raise ValueError('子问题新增原问题之外的中文内容：'+''.join(sorted(added)))
        original_english = {t.lower() for t in english_terms(question)}
        question_words = {'definition','and','key','features','in','textbook','what','how','is','are','the','of','roles','differences','between'}
        extra_english = {t.lower() for t in english_terms(query)}-original_english-question_words
        if extra_english:
            raise ValueError('子问题新增原问题之外的英文术语')
        key = (query.strip(), chapter)
        if key in seen:
            if len(chapters) > 1:
                repairs.append({'entry': entry_index, 'kind': 'duplicate_within_chapter', 'chapter': chapter})
                continue
            raise ValueError('重复子问题')
        seen.add(key)
        queries.append({'query': query.strip(), 'chapter': chapter})
    if chapters and set(chapters) != {q['chapter'] for q in queries}:
        raise ValueError('计划遗漏用户指定章节')
    if len(chapters) > 1:
        grouped = []
        for chapter in chapters:
            texts = [q['query'] for q in queries if q['chapter'] == chapter]
            query = '；'.join(texts)
            if len(query) > 400:
                raise ValueError('同章节合并后子问题过长')
            if len(texts) > 1:
                repairs.append({'kind': 'merge_same_chapter', 'chapter': chapter, 'count': len(texts)})
            grouped.append({'query': query, 'chapter': chapter})
        queries = grouped
    # Protect case-insensitive acronyms and product identifiers from being dropped.
    terms = {t.lower() for t in english_terms(question)}
    joined = {t.lower() for q in queries for t in english_terms(q['query'])}
    if terms - joined:
        raise ValueError('计划遗漏原问题英文术语')
    return {'original_question': question, 'route': 'split', 'reason': 'validated_model_plan',
            'queries': queries, 'normalizations': repairs}


def chapter_filter(rows, number):
    names = sorted({r['chapter'] for r in rows if explicit_chapters(r.get('chapter', '')) == [number]})
    if not names:
        raise ValueError('正文索引没有指定章节：' + str(number))
    return {'$and': [{'section_type': 'body'}, {'chapter': {'$in': names}}]}


def merge_evidence(queries, lists, limit=5):
    if len(queries) != len(lists) or not queries or limit < len(queries):
        raise ValueError('计划、证据列表或最终片段数不匹配')
    lists = [unique_rows(rows) for rows in lists]
    all_rows, labels = {}, {}
    for query, rows in zip(queries, lists):
        for row in rows:
            cid = row['chunk_id']
            if cid in all_rows and not same_source(all_rows[cid], row):
                raise ValueError('跨子问题分片正文或来源冲突：' + cid)
            all_rows.setdefault(cid, row)
            labels.setdefault(cid, [])
            if query['query'] not in labels[cid]:
                labels[cid].append(query['query'])
    selected, seen = [], set()
    # Each nonempty query gets its first unique candidate before filling more slots.
    positions = [0] * len(lists)
    while len(selected) < limit:
        added = False
        for i, rows in enumerate(lists):
            while positions[i] < len(rows) and rows[positions[i]]['chunk_id'] in seen:
                positions[i] += 1
            if positions[i] == len(rows):
                continue
            row = rows[positions[i]]
            positions[i] += 1
            seen.add(row['chunk_id'])
            selected.append({**row, 'matched_queries': labels[row['chunk_id']],
                             'retrieval_method': 'subquery+bm25+dense+rrf' if len(queries) > 1 else 'bm25+dense+rrf'})
            added = True
            if len(selected) == limit:
                break
        if not added:
            break
    return selected
