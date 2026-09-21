import tempfile, unittest
from pathlib import Path
from media_contracts import EvidenceClaim, QAGate
from media_spider import MediaSpider, OfflineAdapter

ROOT = Path(__file__).resolve().parents[1]
class MediaSpiderTests(unittest.TestCase):
    def test_claims_fail_closed(self):
        with self.assertRaises(ValueError): EvidenceClaim("x","x","",.5,"2026-09-21T00:00:00Z","historical").validate()
    def test_rights_missing_is_no_go(self):
        self.assertEqual(QAGate(False,True,True,True,False).decision(), "no_go")
    def test_publish_never_enabled(self):
        self.assertFalse(QAGate(True,True,True,True,True,True).publish_allowed)
    def test_offline_pilot_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            spider=MediaSpider(OfflineAdapter(ROOT/'fixtures'), d)
            a=spider.run_pilot(); b=spider.run_pilot()
            self.assertEqual(a,b); self.assertEqual(a['qa_decision'],'go_draft'); self.assertFalse(a['publish_allowed'])
if __name__ == '__main__': unittest.main()
