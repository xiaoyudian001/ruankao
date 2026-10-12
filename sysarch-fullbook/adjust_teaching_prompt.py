"""Update only the approved teaching instructions in the existing QA flow."""
import copy, json, time
from pathlib import Path
from langflow_api import LangflowAPI

FLOW='2e38f267-52d8-484f-bc4a-81ad7a2e3436'
PROMPT='Prompt Template-fzcHC'
ROOT=Path(r'F:\daily\output\sysarch-teaching-prompt')

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    api=LangflowAPI(); flow=api.call('/flows/'+FLOW)
    original=copy.deepcopy(flow['data']); updated=copy.deepcopy(original)
    nodes={n['id']:n for n in updated['nodes']}
    field=nodes[PROMPT]['data']['node']['template']['template']
    before=field['value']
    changes={
      '- 只使用教材片段中有依据的信息。':'- 教材结论只使用教材片段中有依据的信息；额外的教学解释必须按下方“辅助理解”规则处理。',
      '- 只做有来源的摘录、改写和整理，不添加片段未明示的实现机制、优势、保证或扩展说明。保持原文限定程度，不把“应减少依赖”改写为“绝无依赖”。':
      '- 教材是回答事实和考试术语的主要依据。先准确回答教材结论，保留定义、条件、公式和专业术语，并标注直接支持结论的出处。保持原文限定程度，不把“应减少依赖”改写为“绝无依赖”。\n'
      '- 在教材结论之后，可按用户需要增加通俗解释、简单例子、概念比较或记忆提示，帮助理解，避免机械重复原文。\n'
      '- 超出教材片段明确内容的补充，必须独立标为“辅助理解”；例子须说明是假设示例，不得冒充教材原文，不得给补充内容附上不支持它的教材引用或页码。\n'
      '- 辅助讲解不得改变教材定义、遗漏限定条件，不得编造考试频率、标准答案或评分要求。不确定的补充不要写成确定事实。\n'
      '- 检索资料不足时明确说明不足，不用模型常识冒充教材结论。简单问题简短回答，复杂问题再展开，不强制每次输出所有部分。',
      '- 每项知识点或表格行就近标注直接支持该结论的片段编号；仅主题相似的片段不能作为依据。比较表只填写教材明确提供的对比信息，不为了凑齐表格而推断研究核心或属性。':
      '- 教材结论中的每项知识点或表格行，就近标注直接支持该结论的片段编号；仅主题相似的片段不能作为依据。教材依据部分的比较表只填写教材明确提供的信息；需要教学推导时单独放入“辅助理解”，明确它是解释，不是教材原文，不把它当作新的事实、保证或考试结论。',
      '- 问题已经回答完整后结束，不额外添加“要点说明”或泛化总结。':
      '- 先直接回答，再按需要补充辅助理解；已回答完整时结束，避免重复总结或无关展开。',
    }
    for old,new in changes.items():
        assert before.count(old)==1,'Prompt has changed; inspect before modifying'
        before=before.replace(old,new)
    field['value']=before
    restored=copy.deepcopy(updated)
    next(n for n in restored['nodes'] if n['id']==PROMPT)['data']['node']['template']['template']['value']=next(n for n in original['nodes'] if n['id']==PROMPT)['data']['node']['template']['template']['value']
    assert restored==original,'Unexpected non-prompt change'
    original_prompt=next(n for n in original['nodes'] if n['id']==PROMPT)['data']['node']['template']['template']['value']
    assert original_prompt.split('- 引用须给出',1)[1]==before.split('- 引用须给出',1)[1]
    stamp=time.strftime('%Y%m%d-%H%M%S')
    (ROOT/f'prompt-before-{stamp}.txt').write_text(original_prompt,encoding='utf-8')
    (ROOT/'prompt-after.txt').write_text(before,encoding='utf-8')
    assert api.call('/flows/'+FLOW)['data']==original,'Concurrent flow edit'
    api.call('/flows/'+FLOW,{'data':updated},'PATCH')
    saved=api.call('/flows/'+FLOW)
    assert saved['data']==updated,'Saved flow differs'
    assert nodes['LanguageModelComponent-BpTTF']['data']['node']['template']['temperature']['value']==0.2
    assert nodes['Knowledge-Y8gm2']['data']['node']['template']['knowledge_base']['value']=='SysArchTutorRAGv3'
    result={'flow_id':FLOW,'prompt_only_changed':True,'temperature':0.2,'kb':'SysArchTutorRAGv3','citation_rule_unchanged':True,'backup':str(ROOT/f'prompt-before-{stamp}.txt')}
    (ROOT/'configuration-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
