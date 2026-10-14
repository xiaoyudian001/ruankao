"""Only provider-reported answer generation usage; missing is never zero."""
import re

def new_usage():
 return {'scope':'answer_generation','inputTokens':None,'outputTokens':None,'totalTokens':None,'reportedCalls':0,'unreportedCalls':0,'models':[]}

def response_usage(response):
 value=getattr(response,'usage_metadata',None)
 if not isinstance(value,dict):
  metadata=getattr(response,'response_metadata',None)
  value=metadata.get('token_usage') if isinstance(metadata,dict) else None
 if not isinstance(value,dict):return None
 inp=value.get('input_tokens',value.get('prompt_tokens'));out=value.get('output_tokens',value.get('completion_tokens'))
 if any(type(n) is not int or n<0 or n>100000000 for n in (inp,out)):return None
 total=value.get('total_tokens',inp+out)
 if type(total) is not int or total!=inp+out or total>100000000:return None
 return {'inputTokens':inp,'outputTokens':out,'totalTokens':total}

def add_response(ledger,response,model):
 value=response_usage(response)
 if value is None:ledger['unreportedCalls']+=1
 else:
  for key,n in value.items():ledger[key]=(ledger[key] or 0)+n
  ledger['reportedCalls']+=1
 if isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_.:/ -]{1,100}',model) and model not in ledger['models'] and len(ledger['models'])<4:ledger['models'].append(model)

def merge_usage(ledger,value):
 if not isinstance(value,dict) or value.get('scope')!='answer_generation':ledger['unreportedCalls']+=1;return
 reported=value.get('reportedCalls');missing=value.get('unreportedCalls')
 if any(type(n) is not int or n<0 or n>100 for n in (reported,missing)):ledger['unreportedCalls']+=1;return
 tokens=[value.get(k) for k in ('inputTokens','outputTokens','totalTokens')]
 if reported and (any(type(n) is not int or n<0 or n>100000000 for n in tokens) or tokens[0]+tokens[1]!=tokens[2]):ledger['unreportedCalls']+=1;return
 if not reported and any(n is not None for n in tokens):ledger['unreportedCalls']+=1;return
 ledger['reportedCalls']+=reported;ledger['unreportedCalls']+=missing
 if reported:
  for k,n in zip(('inputTokens','outputTokens','totalTokens'),tokens):ledger[k]=(ledger[k] or 0)+n
 for model in value.get('models',[]):
  if isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_.:/ -]{1,100}',model) and model not in ledger['models'] and len(ledger['models'])<4:ledger['models'].append(model)

def generation_error_payload(usage,error):
 # Transport only a safe category, never raw provider errors or request text.
 reasons=('Incomplete exam envelope','Incomplete answer envelope','Invalid answer JSON','Unknown answer citation','Unknown figure','Invalid visual answer','Invalid visual text','Invalid mixed QA envelope','Unexpected answer output','Incomplete figure declaration')
 reason=next((r for r in reasons if r in str(error)),'Answer generation failed')
 return {'generationError':{'kind':'TimeoutError' if isinstance(error,TimeoutError) else 'ValueError','reason':reason},'tokenUsage':usage}
