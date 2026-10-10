import re,sqlite3,unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]
class ReviewTransactions(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript((ROOT/'drizzle/0005_safe_chameleon.sql').read_text())
        self.db.execute("INSERT INTO textbook_favorites VALUES('f','owner','job','问题',NULL,'答案','[]',1)")
        self.db.execute("INSERT INTO textbook_cards(id,owner_id,favorite_id,front,back,due_date,created_at,updated_at) VALUES('c','owner','f','问题','答案','2026-10-10',1,1)")
        source=(ROOT/'lib/review/store.ts').read_text()
        self.update=re.search(r'REVIEW_UPDATE_SQL=`(.+?)`',source,re.S)[1]
        self.insert=re.search(r'REVIEW_INSERT_SQL=`(.+?)`',source,re.S)[1]
    def review(self,key,version=0,owner='owner'):
        with self.db:
            result=self.db.execute(self.update,(1,'2026-10-11',key,2,'c',owner,version,key)).rowcount
            self.db.execute(self.insert,(key,'remembered','我的回答','2026-10-10','2026-10-11',version+1,2,'c',owner,key,version+1))
        return result
    def test_retry_is_idempotent(self):
        self.assertEqual(self.review('request1'),1)
        self.assertEqual(self.review('request1'),0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM textbook_reviews').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT version FROM textbook_cards').fetchone()[0],1)
    def test_stale_version_cannot_create_another_review(self):
        self.review('request1')
        self.assertEqual(self.review('request2'),0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM textbook_reviews').fetchone()[0],1)
        self.assertEqual(self.review('request3',1),1)
    def test_owner_isolation(self):
        self.assertEqual(self.review('request1',owner='someone_else'),0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM textbook_reviews').fetchone()[0],0)
    def test_duplicate_favorite_and_card_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO textbook_favorites VALUES('f2','owner','job','问题',NULL,'答案','[]',1)")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO textbook_cards(id,owner_id,favorite_id,front,back,due_date,created_at,updated_at) VALUES('c2','owner','f','问题','答案','2026-10-10',1,1)")
if __name__=='__main__':unittest.main()
