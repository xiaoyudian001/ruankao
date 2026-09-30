import re, sqlite3, unittest
from pathlib import Path

class QueueTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE textbook_jobs(id TEXT PRIMARY KEY, question TEXT, session_id TEXT, status TEXT, lease TEXT, leased_at INTEGER, created_at INTEGER, answer TEXT, error TEXT, completed_at INTEGER, elapsed_ms INTEGER);')
        code=(Path(__file__).parents[1]/'lib/textbook/server.ts').read_text(encoding='utf-8')
        self.claim=re.search(r'CLAIM_SQL = `(.+?)`',code,re.S)[1]
        self.complete=re.search(r'COMPLETE_SQL = `(.+?)`',code,re.S)[1]
        self.db.execute("INSERT INTO textbook_jobs VALUES ('one','MTBF','session','queued',NULL,NULL,10,NULL,NULL,NULL,NULL)")
        self.db.execute("INSERT INTO textbook_jobs VALUES ('two','MTTR','session2','queued',NULL,NULL,11,NULL,NULL,NULL,NULL)")
    def test_one_running_and_reject_wrong_or_expired_completion(self):
        self.assertEqual(self.db.execute(self.claim,('lease-1',20)).fetchone()[0],'one')
        self.assertIsNone(self.db.execute(self.claim,('lease-2',21)).fetchone())
        args=['done','answer',None,22,2000,'one','wrong',0]
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        args[-2]='lease-1';args[-1]=21
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        args[-1]=0
        self.assertEqual(self.db.execute(self.complete,args).fetchone()[0],'one')
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        self.assertEqual(self.db.execute(self.claim,('lease-2',23)).fetchone()[0],'two')
    def tearDown(self): self.db.close()

if __name__=='__main__':unittest.main()
