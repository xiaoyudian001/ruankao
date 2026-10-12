import time
from pathlib import Path
import psutil

script=Path(r'F:\daily\sysarch-fullbook\run_fullbook.py')
matches=[]
for process in psutil.process_iter(['pid','cmdline']):
    command=process.info['cmdline'] or []
    if any(arg.lower()==str(script).lower() for arg in command) and '--pilot' not in command:
        matches.append(process)
ids={p.pid for p in matches}
leaves=[p for p in matches if not any(child.pid in ids for child in p.children())]
assert len(leaves)==1, f'Expected one owned runner process tree; found {len(leaves)} leaves'
process=leaves[0]
assert ids<={process.pid}|{parent.pid for parent in process.parents()}, 'Multiple independent runners found'
deadline=time.monotonic()+90
while time.monotonic()<deadline:
    active=any(connection.raddr and connection.raddr.port==7860 and connection.status=='ESTABLISHED'
               for connection in process.net_connections(kind='tcp'))
    if not active:
        process.terminate()
        process.wait(timeout=10)
        print('Owned runner stopped at local non-ingestion phase; pending rows and progress preserved.',flush=True)
        break
    time.sleep(.5)
else:
    raise RuntimeError('No safe restart point found; runner left running')
