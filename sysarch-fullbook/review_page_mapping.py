import json
from collections import Counter
from scan_printed_pages import ROOT, SOURCE
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

def candidates(row):
    result=[]
    for item in row['items']:
        text=item['text'].strip()
        xs=[point[0] for point in item['box']]
        # Printed number sits at the extreme left or right inside blue ornaments.
        if text.isdigit() and (max(xs)<row['width']*.17 or min(xs)>row['width']*.84):
            result.append((int(text),item['score']))
    return result

def review():
    rows=json.loads((ROOT/'header-ocr.json').read_text(encoding='utf-8'))
    matches=[]; missing=[]; conflicts=[]
    for physical in range(18,728):
        if str(physical) not in rows: continue
        nums=candidates(rows[str(physical)])
        if any(number==physical-15 for number,score in nums): matches.append(physical)
        elif nums: conflicts.append({'pdf_page':physical,'candidates':nums})
        else: missing.append(physical)
    result={'scanned':len(rows),'matched':len(matches),'missing':missing,'conflicts':conflicts}
    save_path=ROOT/'scan-review.json'
    save_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return result

def sheet(pages,part='header',filename='exception-headers.png'):
    crops=[]
    with pdfium.PdfDocument(str(SOURCE)) as pdf:
        for p in pages:
            page=pdf[p-1]
            im=page.render(scale=2.5).to_pil().convert('RGB')
            crop=im.crop((0,0,im.width,round(im.height*.15))) if part=='header' else im.crop((0,round(im.height*.90),im.width,im.height))
            crop=crop.resize((1000,round(crop.height*1000/crop.width)))
            crops.append((p,crop));page.close()
    canvas=Image.new('RGB',(1000,sum(im.height+25 for _,im in crops)),'white')
    draw=ImageDraw.Draw(canvas);y=0
    for p,im in crops:
        draw.text((5,y+3),f'PDF {p}',fill='black');canvas.paste(im,(0,y+25));y+=im.height+25
    canvas.save(ROOT/filename)
    print(ROOT/filename)

def exception_sheets():
    pages=review()['missing']
    with pdfium.PdfDocument(str(SOURCE)) as pdf:
        for i in range(0,len(pages),8):
            crops=[]
            for p in pages[i:i+8]:
                page=pdf[p-1];im=page.render(scale=2.5).to_pil().convert('RGB')
                top=im.crop((0,0,im.width,round(im.height*.17)))
                bottom=im.crop((0,round(im.height*.9),im.width,im.height))
                top=top.resize((750,round(top.height*750/top.width)))
                bottom=bottom.resize((750,round(bottom.height*750/bottom.width)))
                row=Image.new('RGB',(1500,top.height),'white');row.paste(top,(0,0));row.paste(bottom,(750,0))
                crops.append((p,row));page.close()
            canvas=Image.new('RGB',(1500,sum(im.height+25 for _,im in crops)),'white')
            draw=ImageDraw.Draw(canvas);y=0
            for p,im in crops:
                draw.text((5,y+3),f'PDF {p}: header (left), footer (right)',fill='black')
                canvas.paste(im,(0,y+25));y+=im.height+25
            path=ROOT/f'exception-review-{i//8+1}.png';canvas.save(path);print(path)

if __name__=='__main__':
    review()
