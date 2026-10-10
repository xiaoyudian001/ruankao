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
        self.db.execute("ALTER TABLE textbook_jobs ADD retrieval_mode TEXT NOT NULL DEFAULT 'default'")
        self.db.execute("UPDATE textbook_jobs SET retrieval_mode='complete' WHERE id='two'")
        self.db.executescript("ALTER TABLE textbook_jobs ADD history_json TEXT NOT NULL DEFAULT '[]'; ALTER TABLE textbook_jobs ADD retrieval_query TEXT; ALTER TABLE textbook_jobs ADD rewrite_route TEXT; ALTER TABLE textbook_jobs ADD owner_id TEXT;")
        self.db.execute("ALTER TABLE textbook_jobs ADD references_json TEXT NOT NULL DEFAULT '[]'")
    def test_one_running_and_reject_wrong_or_expired_completion(self):
        self.assertEqual(self.db.execute(self.claim,('lease-1',20)).fetchone()[0],'one')
        self.assertIsNone(self.db.execute(self.claim,('lease-2',21)).fetchone())
        args=['done','answer',None,22,2000,'MTBF','direct','[]','one','wrong',0]
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        args[-2]='lease-1';args[-1]=21
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        args[-1]=0
        self.assertEqual(self.db.execute(self.complete,args).fetchone()[0],'one')
        self.assertIsNone(self.db.execute(self.complete,args).fetchone())
        claimed=self.db.execute(self.claim,('lease-2',23)).fetchone()
        self.assertEqual(claimed[0],'two')
        self.assertEqual(claimed[-2],'complete')
        self.assertEqual(claimed[-1],'[]')

    def test_history_sql_excludes_other_sessions_owners_and_failed_rows(self):
        code=(Path(__file__).parents[1]/'lib/textbook/server.ts').read_text(encoding='utf-8')
        history=re.search(r'HISTORY_SQL = `(.+?)`',code,re.S)[1]
        self.db.execute("UPDATE textbook_jobs SET owner_id='alice',session_id='s',status='done',answer='a' WHERE id='one'")
        for ident,owner,session,status,time in [('foreign','bob','s','done',50),('other','alice','other','done',60),('failed','alice','s','failed',70),('running','alice','s','running',80)]:
            self.db.execute('INSERT INTO textbook_jobs(id,owner_id,session_id,status,question,answer,created_at) VALUES(?,?,?,?,?,?,?)',(ident,owner,session,status,ident,'a',time))
        rows=self.db.execute(history,('alice','s')).fetchall()
        self.assertEqual(rows,[('MTBF','a')])
        self.assertEqual(self.db.execute(history,('alice','new')).fetchall(),[])

    def test_conversation_migration_defaults_and_preserves_history(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE textbook_jobs(id TEXT, question TEXT); INSERT INTO textbook_jobs VALUES ("old","MTBF"); CREATE TABLE textbook_bridge(id TEXT); INSERT INTO textbook_bridge VALUES ("desktop");')
        db.executescript((Path(__file__).parents[1]/'drizzle/0003_panoramic_violations.sql').read_text(encoding='utf-8'))
        self.assertEqual(db.execute('SELECT question,history_json,retrieval_query,rewrite_route FROM textbook_jobs').fetchone(),('MTBF','[]',None,None))
        self.assertEqual(db.execute('SELECT conversation_ready FROM textbook_bridge').fetchone()[0],0)
        db.close()

    def test_mode_migration_defaults_historical_rows(self):
        self.assertEqual(self.db.execute("SELECT retrieval_mode FROM textbook_jobs WHERE id='one'").fetchone()[0],'default')
        # Run actual generated migration on the old schema, not a hand-written approximation.
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE textbook_jobs(id TEXT); INSERT INTO textbook_jobs VALUES ("old"); CREATE TABLE textbook_bridge(id TEXT); INSERT INTO textbook_bridge VALUES ("desktop");')
        sql=(Path(__file__).parents[1]/'drizzle/0002_naive_war_machine.sql').read_text(encoding='utf-8')
        db.executescript(sql)
        self.assertEqual(db.execute('SELECT retrieval_mode FROM textbook_jobs').fetchone()[0],'default')
        self.assertEqual(db.execute('SELECT modes FROM textbook_bridge').fetchone()[0],'["default"]')
        db.close()

    def test_page_lease_rejects_stale_upload_and_deduplicates_claim(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE textbook_jobs(id TEXT); CREATE TABLE textbook_bridge(id TEXT);')
        db.executescript((Path(__file__).parents[1]/'drizzle/0004_good_wind_dancer.sql').read_text(encoding='utf-8'))
        code=(Path(__file__).parents[1]/'lib/textbook/sources.ts').read_text(encoding='utf-8')
        claim=re.search(r'PAGE_CLAIM_SQL=`(.+?)`',code,re.S)[1]
        finish=re.search(r'PAGE_FINISH_SQL=`(.+?)`',code,re.S)[1]
        db.executemany("INSERT INTO textbook_pages(page,status,created_at,updated_at) VALUES(?,'queued',10,10)",[(323,),(324,)])
        self.assertEqual(db.execute(claim,('a',20)).fetchone(),(323,'a'))
        self.assertIsNone(db.execute(claim,('b',21)).fetchone())
        self.assertIsNone(db.execute(finish,('key',22,323,'b',0)).fetchone())
        self.assertIsNone(db.execute(finish,('key',22,323,'a',21)).fetchone())
        self.assertEqual(db.execute(finish,('key',22,323,'a',0)).fetchone(),(323,))
        self.assertEqual(db.execute(claim,('b',23)).fetchone(),(324,'b'))
        db.close()
    def tearDown(self): self.db.close()

if __name__=='__main__':unittest.main()
