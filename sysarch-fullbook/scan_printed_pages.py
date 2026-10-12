"""Read printed header page numbers without altering source PDF or cached text."""
import argparse
import json
import time
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from core import save_json_atomic
from parse_book import SOURCE

ROOT = Path(r'F:\daily\output\sysarch-page-citations')
SAMPLES = [18, 19, 20, 38, 119, 320, 323, 418, 419, 420, 614, 628, 647, 727]

def header(pdf, physical):
    page = pdf[physical - 1]
    image = page.render(scale=2.5).to_pil().convert('RGB')
    crop = image.crop((0, 0, image.width, round(image.height * .105)))
    page.close()
    return crop

def contact():
    ROOT.mkdir(parents=True, exist_ok=True)
    with pdfium.PdfDocument(str(SOURCE)) as pdf:
        images = [header(pdf, p) for p in SAMPLES]
    width = 1400
    heights = [round(im.height * width / im.width) + 28 for im in images]
    canvas = Image.new('RGB', (width, sum(heights)), 'white')
    draw = ImageDraw.Draw(canvas)
    y = 0
    for p, im, h in zip(SAMPLES, images, heights):
        draw.text((5, y + 4), f'PDF {p}', fill='black')
        canvas.paste(im.resize((width, h - 28)), (0, y + 28))
        y += h
    canvas.save(ROOT / 'header-samples.png')
    print(ROOT / 'header-samples.png')

def scan(start=1, end=728):
    import rapidocr
    from rapidocr import RapidOCR
    models = Path(rapidocr.__file__).parent / 'models'
    engine = RapidOCR(params={
        'Det.model_path': str(models / 'PP-OCRv6_det_small.onnx'),
        'Rec.model_path': str(models / 'PP-OCRv6_rec_small.onnx'),
        'Cls.model_path': str(models / 'ch_ppocr_mobile_v2.0_cls_mobile.onnx'),
        'EngineConfig.onnxruntime.intra_op_num_threads': 4,
        'EngineConfig.onnxruntime.inter_op_num_threads': 1,
        'Global.log_level': 'warning',
        'Global.text_score': .1,
        'Det.limit_type': 'max',
        'Det.limit_side_len': 1600,
    })
    ROOT.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'header-ocr.json'
    rows = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
    began = time.time()
    with pdfium.PdfDocument(str(SOURCE)) as pdf:
        for p in range(start, end + 1):
            if str(p) in rows:
                continue
            im = header(pdf, p)
            out = engine(im, use_cls=False)
            items = []
            if out.txts:
                for box, txt, score in zip(out.boxes, out.txts, out.scores):
                    items.append({'text': txt, 'score': float(score), 'box': box.tolist()})
            rows[str(p)] = {'pdf_page': p, 'width': im.width, 'height': im.height, 'items': items}
            save_json_atomic(cache, rows)
            if p % 20 == 0 or p == end:
                print('SCANNED', p, 'seconds', round(time.time() - began, 1), flush=True)
    print('COMPLETE', len(rows), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--contact', action='store_true')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=728)
    args = parser.parse_args()
    contact() if args.contact else scan(args.start, args.end)
