import json
from pathlib import Path
from unittest import TestCase

from bullet_spider import OfflineFixtureAdapter, ResponseType, run_bullet_spider, signal_from_mapping


FIXTURE = Path(__file__).parent / "fixtures" / "bullet_signals.json"


class BulletSpiderTests(TestCase):
    def setUp(self):
        self.rows = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_offline_default_makes_no_claims(self):
        result = run_bullet_spider({"topic": "anything"})
        self.assertEqual(result["status"], "offline_safe_no_sources_configured")
        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["briefs"], [])

    def test_deterministic_ranked_assessment_and_draft_only_brief(self):
        adapter = OfflineFixtureAdapter(self.rows)
        result = run_bullet_spider({"geography": "MA", "language": "ar", "as_of": "2026-09-21T00:00:00Z"}, [adapter])
        self.assertEqual(len(result["opportunities"]), 1)
        opportunity = result["opportunities"][0]
        brief = result["briefs"][0]
        self.assertEqual(opportunity["response_type"], ResponseType.LOCALIZATION.value)
        self.assertEqual(opportunity["observed_at"], "2026-09-20T17:00:00Z")
        self.assertIn("https://trends.example.org/ma/budget-template", opportunity["source_urls"])
        self.assertIn("proxy, not verified sales", " ".join(opportunity["limitations"]))
        self.assertEqual(brief["status"], "draft_requires_human_approval")
        self.assertFalse(brief["listing_draft"]["publish"])
        self.assertIn("human_publish_approval", brief["review_gates"])
        self.assertEqual(brief["pricing_draft"]["amount"], None)
        self.assertTrue(opportunity["affiliate_eligible"])
        self.assertIsNotNone(opportunity["affiliate_score"])
        self.assertEqual(opportunity["decision"], "go")


    def test_missing_commission_means_no_recommendation_or_brief(self):
        row = dict(self.rows[0])
        row.pop("commission_rate", None)
        row["category"] = "affiliate"
        result = run_bullet_spider(
            {"geography": "MA", "as_of": "2026-09-21T00:00:00Z"},
            [OfflineFixtureAdapter([row])],
        )
        self.assertFalse(result["opportunities"][0]["affiliate_eligible"])
        self.assertIsNone(result["opportunities"][0]["affiliate_score"])
        self.assertEqual(result["briefs"], [])
        self.assertIn("missing commission rate", result["opportunities"][0]["limitations"])



    def test_missing_production_economics_is_no_go_and_no_brief(self):
        row = dict(self.rows[0])
        row.pop("production_cost", None)
        result = run_bullet_spider(
            {"geography": "MA", "as_of": "2026-09-21T00:00:00Z"},
            [OfflineFixtureAdapter([row])],
        )
        opportunity = result["opportunities"][0]
        self.assertEqual(opportunity["decision"], "no_go")
        self.assertIn("production cost", opportunity["decision_blockers"])
        self.assertEqual(result["briefs"], [])

    def test_supported_categories_route_to_specialists(self):
        expected = {
            "digital_product": "digital_products_spider",
            "digital_book": "book_spider",
            "product_design": "visual_spider",
            "decor_art": "visual_spider",
            "affiliate": "affiliate_spider",
        }
        for category, spider in expected.items():
            row = dict(self.rows[0], signal_id=category, category=category)
            result = run_bullet_spider(
                {"geography": "MA", "as_of": "2026-09-21T00:00:00Z"},
                [OfflineFixtureAdapter([row])],
            )
            self.assertEqual(result["opportunities"][0]["category"], category)
            self.assertIn(spider, result["briefs"][0]["assigned_spiders"])

    def test_market_spy_shape_is_accepted_without_inventing_sales(self):
        signal = signal_from_mapping({
            "opportunity_id": "spy-1",
            "topic": "3D printable desk organizer",
            "geography": "FR",
            "observed_at": "2026-09-20T19:00:00+02:00",
            "source_urls": ["https://example.org/public-trend"],
            "metric": "trend_index",
            "value": 63,
            "evidence_type": "proxy",
            "confidence": 0.7,
            "competition_score": 0.4,
            "limitations": ["No verified transaction count."],
        })
        self.assertEqual(signal.metric_kind, "proxy")
        self.assertEqual(signal.observed_at, "2026-09-20T17:00:00Z")
        self.assertIn("No verified", signal.limitations[0])

    def test_rejects_untraceable_or_naive_signal(self):
        bad = dict(self.rows[0])
        bad["source_url"] = "private-history://user/123"
        with self.assertRaises(ValueError):
            signal_from_mapping(bad)
        bad = dict(self.rows[0])
        bad["observed_at"] = "2026-09-20T18:00:00"
        with self.assertRaises(ValueError):
            signal_from_mapping(bad)
