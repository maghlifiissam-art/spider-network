import json, tempfile, unittest
from pathlib import Path
from publish_contracts import PublishJob, PublishReceipt, PublishPolicy
from publish_spider import PublishSpider, job_from_media_handoff, load_policy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "publish_job.json").read_text(encoding="utf-8"))


class PublishContractTests(unittest.TestCase):
    def test_job_validates_fixture(self):
        PublishJob(**FIXTURE).validate()

    def test_unknown_platform_rejected(self):
        bad = dict(FIXTURE, platforms=["myspace"])
        with self.assertRaises(ValueError):
            PublishJob(**bad).validate()

    def test_empty_platforms_rejected(self):
        with self.assertRaises(ValueError):
            PublishJob(**dict(FIXTURE, platforms=[])).validate()

    def test_hashtag_format_enforced(self):
        with self.assertRaises(ValueError):
            PublishJob(**dict(FIXTURE, hashtags=["#قصص"])).validate()

    def test_wrong_contract_version_rejected(self):
        with self.assertRaises(ValueError):
            PublishJob(**dict(FIXTURE, contract_version="publish.v0")).validate()
        with self.assertRaises(ValueError):
            PublishReceipt("j", "youtube", "published", contract_version="publish.v0").validate()


class PublishSpiderTests(unittest.TestCase):
    def test_dry_run_default_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            import publish_spider
            old = publish_spider.RECEIPTS_PATH
            publish_spider.RECEIPTS_PATH = Path(d) / "receipts.json"
            try:
                receipts = PublishSpider().run_job(FIXTURE)
            finally:
                publish_spider.RECEIPTS_PATH = old
        self.assertEqual(len(receipts), 4)
        self.assertTrue(all(r["status"] == "dry_run" for r in receipts))

    def test_disabled_platform_is_skipped(self):
        policy = PublishPolicy(dry_run=True, enabled_platforms=("youtube",))
        with tempfile.TemporaryDirectory() as d:
            import publish_spider
            old = publish_spider.RECEIPTS_PATH
            publish_spider.RECEIPTS_PATH = Path(d) / "receipts.json"
            try:
                receipts = PublishSpider(policy).run_job(FIXTURE)
            finally:
                publish_spider.RECEIPTS_PATH = old
        by_platform = {r["platform"]: r["status"] for r in receipts}
        self.assertEqual(by_platform["youtube"], "dry_run")
        self.assertEqual(by_platform["tiktok"], "skipped")

    def test_policy_loads_defaults_without_yaml_file(self):
        policy = load_policy(ROOT / "config" / "does_not_exist.yaml")
        self.assertTrue(policy.dry_run)

    def test_media_handoff_bridge(self):
        handoff = {"run_id": "r1", "payload": {"video_path": "v.mp4", "title": "t", "description": "d"}}
        job = job_from_media_handoff(handoff, "job-1", platforms=["youtube"], campaign_id="c1")
        self.assertEqual(job["sender"], "media_spider")
        self.assertEqual(job["run_id"], "r1")
        PublishJob(**job).validate()


if __name__ == "__main__":
    unittest.main()
