"""Safe user-visible failure categories; never return raw provider bodies."""
from urllib.error import HTTPError,URLError

def failure_message(error):
 detail=str(error)
 if isinstance(error,HTTPError):
  detail=error.read(16000).decode('utf-8',errors='replace')
 if 'Invalid evidence rank' in detail or 'Invalid critique rank notation' in detail:
  return 'AI 点评的教材引用未通过校验，自动恢复未成功；答案已保存，请重试或核对资料。'
 if any(s in detail for s in ('Incomplete critique envelope','Invalid critique points','Invalid critique boolean','Invalid critique object','Invalid critique text','Invalid model JSON')):
  return 'AI 点评返回的格式不完整，自动恢复未成功；答案已保存，请稍后再次点评。'
 if any(s in detail for s in ('Unknown answer citation','Unknown figure','referenced unused evidence')):
  return '模型答案的教材引用未通过校验，请重新提问。'
 if any(s in detail for s in ('Incomplete exam envelope','Invalid exam','Incomplete figure','Unexpected exam','Invalid visual','Empty visual')):
  return '模型返回的答案格式不完整，自动恢复未成功，请重试。'
 if isinstance(error,TimeoutError) or 'TimeoutError' in detail or 'timed out' in detail:
  return '模型作答超时，请稍后重试；题目和已提交的答案会保留。'
 if isinstance(error,HTTPError):return '本地流程返回服务错误（HTTP '+str(error.code)+'），请稍后重试。'
 if isinstance(error,URLError):return '无法连接本地问答服务，请检查 Langflow 和 Ollama 是否运行。'
 return '问答结果处理失败，请重试；若持续失败，请查看后台日志。'
