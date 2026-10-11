"""Render only whitelisted original PDF pages in a separate connector worker."""
import hashlib
import io
import json
from pathlib import Path
import pypdfium2 as pdfium

BOOK_SHA='edcc38b168485d49a369c9dd8a45a637e91189e16941b31c86196cc4bfe961a9'
ROOT=Path(__file__).resolve().parent.parent


class PageRenderer:
    def __init__(self):
        config=ROOT/'textbook-bridge/page-source.json'
        source=json.loads((config if config.exists() else ROOT/'output/sysarch-fullbook-v2/source.json').read_text(encoding='utf-8'))
        self.path=Path(source['path'])
        with self.path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=BOOK_SHA:
                raise ValueError('Original textbook checksum mismatch')
        self.signature=(self.path.stat().st_size,self.path.stat().st_mtime_ns)
        self.cache=ROOT/'output/sysarch-citation-viewer/pages'
        self.cache.mkdir(parents=True,exist_ok=True)

    def render(self,page,*,refresh=False):
        if type(page) is not int or not 1<=page<=728:
            raise ValueError('Invalid original PDF page')
        stat=self.path.stat()
        if self.signature!=(stat.st_size,stat.st_mtime_ns):
            raise ValueError('Original PDF changed')
        cached=self.cache/f'pdf-{page:04d}-{BOOK_SHA[:12]}.jpg'
        if cached.exists() and not refresh:return cached.read_bytes()
        with pdfium.PdfDocument(str(self.path)) as doc:
            if len(doc)!=728:raise ValueError('Original PDF page count mismatch')
            original=doc[page-1]
            try:
                scale=1600/original.get_width()
                bitmap=original.render(scale=scale)
                try:
                    image=bitmap.to_pil().convert('RGB')
                    buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=88,optimize=True)
                    data=buffer.getvalue();image.close()
                finally:bitmap.close()
            finally:original.close()
        if len(data)>2*1024*1024:raise ValueError('Rendered page too large')
        cached.write_bytes(data)
        return data
