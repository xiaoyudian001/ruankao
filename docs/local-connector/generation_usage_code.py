"""Wrap the existing generation loop without changing any prompt or input."""
def failure_transport(code):
 if 'json.dumps(generation_error_payload(usage,error)' in code:return code
 start=code.index('  for attempt in range(2):')
 # The generation loop is the last class method in this component.
 body=code[start:].rstrip('\n')
 needle='   raw=await asyncio.wait_for('
 if body.count(needle)!=1:raise ValueError('Unexpected invocation contract')
 lines=body.splitlines();line=next(i for i,s in enumerate(lines) if s.startswith(needle))
 call=lines[line];lines[line:line+1]=['   try:', ' '+call, '   except Exception:',"    add_response(usage,None,getattr(model,'model_name',''));raise"]
 wrapped='  try:\n'+'\n'.join(' '+s for s in lines)+'\n  except (GenerationStopped,asyncio.CancelledError):raise\n  except Exception as error:\n   return Message(text=json.dumps(generation_error_payload(usage,error),ensure_ascii=False))\n'
 return code[:start]+wrapped
