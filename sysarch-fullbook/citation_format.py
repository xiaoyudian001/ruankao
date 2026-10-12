def source_hint(row):
    first=str(row.get('pdf_page_start',''))
    last=str(row.get('pdf_page_end',''))
    if not first.isdigit() or not last.isdigit() or int(first)<1 or int(last)<int(first):
        return ''
    filename=str(row.get('source_file','')).replace('\n',' ').strip()
    page=str(int(first)) if int(first)==int(last) else f'{int(first)}～{int(last)}'
    label=f'原PDF第{page}页（物理页）'
    book_first=str(row.get('book_page_start',''))
    book_last=str(row.get('book_page_end',''))
    book_pages=str(row.get('book_pages','')).split(',')
    if (row.get('book_page_mapping_status')=='complete'
            and book_first.isdigit() and book_last.isdigit()
            and int(book_first)>0 and int(book_last)>=int(book_first)
            and all(p.isdigit() for p in book_pages)):
        numbers=[int(p) for p in book_pages]
        expected=list(range(int(book_first),int(book_last)+1))
        if numbers==expected and len(expected)==int(last)-int(first)+1:
            book_page=str(int(book_first)) if int(book_first)==int(book_last) else f'{int(book_first)}～{int(book_last)}'
            label=f'教材第{book_page}页（PDF第{page}页）'
    result=f'来源：{filename}；{label}'
    chapter=str(row.get('chapter','')).strip()
    if chapter and chapter.lower()!='nan':
        result+='；'+chapter
    return result
