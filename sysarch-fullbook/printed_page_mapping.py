"""Create explicit PDF-to-visible-printed-page mapping and chunk metadata."""
import json
from pathlib import Path
from core import save_json_atomic

ROOT=Path(r'F:\daily\output\sysarch-page-citations')
SOURCE_HASH='edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'
VERSION='sysarch-visible-book-pages-v1'

def page_fields(metadata, mapping):
    if metadata.get('source_sha256')!=mapping['source_sha256']:
        raise ValueError('Page map belongs to a different source PDF')
    start=int(metadata['pdf_page_start']);end=int(metadata['pdf_page_end'])
    if start<1 or end<start or end>mapping['pdf_page_count']:
        raise ValueError('Invalid PDF page range')
    entries=[mapping['pages'][str(p)] for p in range(start,end+1)]
    books=[entry['book_page'] for entry in entries if entry['book_page'] is not None]
    complete=len(books)==len(entries) and books==list(range(books[0],books[-1]+1)) if books else False
    return {'book_pages':','.join(map(str,books)),
            'book_page_start':str(books[0]) if complete else '',
            'book_page_end':str(books[-1]) if complete else '',
            'book_page_mapping_status':'complete' if complete else 'partial' if books else 'pdf_only',
            'page_mapping_version':VERSION}

def build_map():
    # Every visible match is independently OCR-read; unprinted pages get no inferred label.
    from review_page_mapping import candidates
    headers=json.loads((ROOT/'header-ocr.json').read_text(encoding='utf-8'))
    assert len(headers)==728, 'Header review must cover whole PDF'
    pages={};conflicts=[];missing=[];verified=[]
    for physical in range(1,729):
        entry={'pdf_page':physical,'book_page':None,'status':'outside_body'}
        if 18<=physical<=727:
            nums=candidates(headers[str(physical)])
            match=next(((n,score) for n,score in nums if n==physical-15),None)
            if match:
                entry.update(book_page=match[0],status='header_ocr_verified',score=match[1])
                verified.append(physical)
            elif nums:
                conflicts.append({'pdf_page':physical,'candidates':nums})
                entry['status']='review_required'
            else:
                entry['status']='no_printed_number'
                missing.append(physical)
        pages[str(physical)]=entry
    assert not conflicts, f'Conflicting page numbers: {conflicts}'
    # Manually reviewed chapter opening pages and the two part-divider pages.
    review=json.loads((ROOT/'unprinted-page-review.json').read_text(encoding='utf-8'))
    assert set(review['no_visible_printed_number'])==set(missing), 'All unmapped body pages require visual review'
    mapping={'version':VERSION,'source_sha256':SOURCE_HASH,'pdf_page_count':728,
             'verified_visible_pages':len(verified),'unprinted_body_pages':missing,
             'method':'OCR of each PDF page header, visual review of all body-page exceptions; no inferred numbers',
             'pages':pages}
    save_json_atomic(ROOT/'page-map.json',mapping)
    print('MAPPING_READY',len(verified),'visible body pages;',len(missing),'unprinted body pages')
    return mapping

if __name__=='__main__': build_map()
