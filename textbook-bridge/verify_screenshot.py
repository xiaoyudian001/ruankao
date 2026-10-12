"""A synthetic screenshot tests real recognition and corrected-text exam generation."""
import base64,json,uuid
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from bridge import LocalFlow
from single_pass import run_single_pass

out=Path('F:/daily/output/sysarch-screenshot');out.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(1200,670),'white');draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
lines=['下列哪项属于系统架构设计师的职责？（单选）','A. 确认和评估需求，给出开发规范','B. 只负责采购服务器，不参与需求评估','C. 只负责录入业务数据','D. 不参与早期质量保证']
for i,line in enumerate(lines):draw.text((40,40+i*75),line,font=font,fill='black')
# Add an input diagram, making preservation visually testable without sending a real exam.
draw.rectangle((50,450,380,530),outline='black',width=3);draw.text((70,470),'用户需求',font=font,fill='black');draw.line((380,490,560,490),fill='black',width=3);draw.polygon([(560,490),(540,480),(540,500)],fill='black');draw.rectangle((560,450,1070,530),outline='black',width=3);draw.text((580,470),'设计与实现',font=font,fill='black');draw.text((45,575),'图示：架构师连接需求与设计实现。',font=font,fill='black')
path=out/'synthetic-question.png';image.save(path);img={'dataUrl':'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode(),'width':1200,'height':670}
local=LocalFlow();recognition=local.recognize_screenshots({'id':str(uuid.uuid4()),'question_images':[img]});(out/'recognition.json').write_text(json.dumps(recognition,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(t in recognition['question'] for t in ('A','B','C','D','需求','采购'))
question=recognition['question']+'\n请结合教材逐项分析，并说明原题图示体现的架构师作用。'
assert len(question)<=2000
job={'id':str(uuid.uuid4()),'session_id':str(uuid.uuid4()),'task_type':'exam','question':question,'question_images':[img],'retrieval_mode':'default','history_json':'[]'}
result=run_single_pass(local,job);(out/'real-verification.json').write_text(json.dumps({'recognition':recognition,'result':result},ensure_ascii=False,indent=2),encoding='utf-8')
assert result['timings']['answerCalls']==1 and result['references'] and 'A' in result['answer'] and '需求' in result['answer']
assert '图' in result['answer'] and '[片段' in result['answer']
print(json.dumps({'passed':True,'recognizedChars':len(recognition['question']),'answerCalls':result['timings']['answerCalls'],'references':len(result['references']),'practice':result.get('practice') is not None,'timings':result['timings']},ensure_ascii=False),flush=True)
