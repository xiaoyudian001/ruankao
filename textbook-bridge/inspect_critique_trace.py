import json,sqlite3
with sqlite3.connect('file:C:/Users/78052/AppData/Roaming/com.LangflowDesktop/data/database.db?mode=ro',uri=True) as db:
 rows=db.execute('SELECT s.name,s.status,s.outputs FROM span s JOIN trace t ON s.trace_id=t.id WHERE t.session_id=? ORDER BY s.start_time DESC LIMIT 4',('critique-verify-recall-critique',)).fetchall()
 for name,status,raw in rows:
  if name=='教材主动回忆点评':
   print(json.dumps({'name':name,'status':status,'outputs':json.loads(raw) if raw else None},ensure_ascii=False)[:8000])
