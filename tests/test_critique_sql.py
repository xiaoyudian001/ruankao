import re,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class CritiqueQueue(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:')
  self.db.executescript('CREATE TABLE textbook_bridge(id TEXT);CREATE TABLE textbook_reviews(id TEXT);CREATE TABLE textbook_jobs(id TEXT,status TEXT);')
  self.db.executescript((ROOT/'drizzle/0006_friendly_arachne.sql').read_text())
  source=(ROOT/'lib/review/critique-server.ts').read_text(encoding='utf-8')
  self.claim=re.search(r'CRITIQUE_CLAIM_SQL=`(.+?)`',source,re.S)[1];self.complete=re.search(r'CRITIQUE_COMPLETE_SQL=`(.+?)`',source,re.S)[1]
  self.db.execute("INSERT INTO textbook_critiques(id,owner_id,card_id,card_version,job_id,front,back,response,references_json,created_at) VALUES('q','o','c',0,'j','问题','答案','我的回忆','[]',1)")
 def test_claim_serializes_against_answer_jobs(self):
  self.db.execute("INSERT INTO textbook_jobs VALUES('j','running')")
  self.assertIsNone(self.db.execute(self.claim,('l',10)).fetchone())
  self.db.execute("UPDATE textbook_jobs SET status='done'")
  self.assertEqual(self.db.execute(self.claim,('l',10)).fetchone()[0],'q')
  self.assertIsNone(self.db.execute(self.claim,('l2',11)).fetchone())
 def test_wrong_lease_and_expiry_cannot_store_result(self):
  self.db.execute(self.claim,('l',10)).fetchone()
  self.assertIsNone(self.db.execute(self.complete,('done','{}',None,20,'q','bad',0)).fetchone())
  self.assertIsNone(self.db.execute(self.complete,('done','{}',None,20,'q','l',11)).fetchone())
  self.assertEqual(self.db.execute(self.complete,('done','{}',None,20,'q','l',0)).fetchone(),('q',))
  self.assertIsNone(self.db.execute(self.complete,('done','{}',None,20,'q','l',0)).fetchone())
if __name__=='__main__':unittest.main()
