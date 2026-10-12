import json,ast,re,hashlib
from bridge import LocalFlow
from pathlib import Path
from single_pass_components import generation_code
state=json.loads(Path(__file__).with_name('single-pass-flows.json').read_text())
flow=LocalFlow().call('/flows/'+state['generation'])
node=next(n for n in flow['data']['nodes'] if n['id']=='SingleEvidenceAnswer-SysArch')
code=node['data']['node']['template']['code']['value']
print(json.dumps({'codeMatches':code==generation_code(),'storedDigest':hashlib.sha256(code.encode()).hexdigest()}))
tree=ast.parse(code);defs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
ns={'json':json,'re':re};exec(compile(defs,'component','exec'),ns)
raw='<final_answer>答案A[片段1]</final_answer><used_figures>[]</used_figures><practice><question>练习</question>'+''.join('<option_'+l+'>内容'+l+'</option_'+l+'>' for l in 'ABCD')+'<correct>A</correct><explanation>说明[片段1]</explanation><ranks>[1]</ranks></practice>'
assert json.loads(ns['serialize_generation'](raw,[],[1],True))['practice']['correct']=='A'
print('Stored component parser passed')
