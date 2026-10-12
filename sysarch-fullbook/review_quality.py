import argparse
import json
from collections import Counter
from pathlib import Path
from core import save_json_atomic
from parse_book import ROOT, SOURCE


def review(render=False):
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'pages').glob('*.json'))]
    flagged = [{'page':r['page'], 'characters':r['characters'], 'flags':r['review_flags'],
                'section': 'front_matter' if r['page'] < 18 else ('back_matter' if r['page'] == 728 else 'body')}
               for r in records if r['review_flags']]
    figures = [p for r in records for p in r['pictures']]
    sparse_body=[r['page'] for r in records if 18<=r['page']<=727 and r['characters']<300]
    watermark_body=[r['page'] for r in records if 18<=r['page']<=727
                    and ('淘宝搜索' in r['markdown'] or '文老师' in r['markdown'])]
    report = {'cached_pages':len(records), 'text_characters':sum(r['characters'] for r in records),
              'flagged_pages':flagged, 'picture_types':dict(Counter(p['kind'] for p in figures)),
              'body_pages_under_300_characters':sparse_body,
              'body_pages_with_scan_watermark_text':watermark_body,
              'saved_figure_files':sum('path' in p for p in figures),
              'diagram_descriptions_pending':sum(p['text_description_status']=='pending' for p in figures),
              'ocr_accuracy_note':'结构和覆盖检查不能证明每个字符准确；原始输出与清理输出都保留供核对。'}
    save_json_atomic(ROOT / 'quality_review.json', report)
    save_json_atomic(ROOT / 'figure_inventory.json', figures)
    preview_rows=list(flagged)
    preview_rows.extend({'page':p,'section':'body (low text)'} for p in sparse_body
                        if p not in {r['page'] for r in flagged})
    if render and preview_rows:
        import pypdfium2 as pdfium
        from PIL import Image, ImageDraw
        count = len(preview_rows)
        sheet = Image.new('RGB', (720, ((count + 2)//3) * 370), 'white')
        draw = ImageDraw.Draw(sheet)
        with pdfium.PdfDocument(str(SOURCE)) as pdf:
            for i,row in enumerate(preview_rows):
                page = pdf[row['page']-1]
                bitmap = page.render(scale=.55)
                picture = bitmap.to_pil().copy()
                picture.thumbnail((230,340))
                x,y=(i%3)*240,(i//3)*370
                sheet.paste(picture,(x,y+25))
                draw.text((x+5,y+5),f"PDF page {row['page']} / {row['section']}",fill='black')
                bitmap.close()
                page.close()
        sheet.save(ROOT / 'flagged_pages_overview.png')
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--render',action='store_true')
    review(parser.parse_args().render)
