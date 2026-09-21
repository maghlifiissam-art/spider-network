import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import market_spy_spider as market

FIXTURES = Path(__file__).parent


class FakeResponse:
    status_code = 200
    def __init__(self, content):
        self.content = content


def fixture_fetch(url, **_kwargs):
    if "trends.google.com" in url:
        return FakeResponse((FIXTURES / "fixtures_google_trends.xml").read_bytes())
    if "itunes.apple.com" in url:
        return FakeResponse((FIXTURES / "fixtures_itunes_lookup.json").read_bytes())
    if "googleapis.com/books" in url:
        return FakeResponse((FIXTURES / "fixtures_google_books.json").read_bytes())
    return FakeResponse((FIXTURES / "fixtures_apple_chart.json").read_bytes())


class MarketSpyTests(TestCase):
    def setUp(self):
        self.cache_patch = patch.object(market, "CACHE_DIR", Path("/tmp/market-spy-test-cache"))
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)
        for path in market.CACHE_DIR.glob("*") if market.CACHE_DIR.exists() else []:
            path.unlink()

    def test_offline_report_preserves_provenance_and_proxy_labels(self):
        report = market.research_market("AI photo", "US", fixture_fetch, market_category="digital_product")
        self.assertTrue(report["signals"])
        self.assertFalse(report["verified_sales_available"])
        self.assertTrue(all(signal["source_url"] for signal in report["signals"]))
        self.assertTrue(all(signal["observed_at"] for signal in report["signals"]))
        self.assertTrue(all(signal["is_proxy"] for signal in report["signals"]))
        self.assertEqual(report["price_summary"]["average"], 4.99)
        self.assertFalse(report["handoff"]["execution_allowed"])
        self.assertEqual(report["handoff"]["affiliate_spider"], [])
        candidate = report["handoff"]["affiliate_candidates_requiring_data"][0]
        self.assertFalse(candidate["affiliate_scorecard"]["eligible"])
        self.assertIsNone(candidate["affiliate_scorecard"]["recommendation_score"])
        self.assertIn("commission", candidate["affiliate_scorecard"]["missing_required_data"])

    def test_unavailable_data_is_not_fabricated(self):
        report = market.build_report("unknown", "MA", [], ["source: unavailable"])
        self.assertEqual(report["signals"], [])
        self.assertIsNone(report["price_summary"]["average"])
        self.assertIn("unavailable", report["source_errors"][0])


    def test_category_profiles_cover_requested_product_families_and_gate_missing_data(self):
        cases = {
            "digital product template": "digital_product",
            "ebook for budgeting": "ebook",
            "SVG design bundle": "design_asset",
            "تابلوات مرسومة ديكور": "wall_art_decor",
            "sticker pack": "sticker",
            "logo for cafe": "logo",
            "children coloring book": "children_coloring_book",
            "القصص المرسومة": "illustrated_story",
            "kitchen product": "physical_product",
        }
        signal = market.Signal(
            product="Example", source_name="fixture", source_url="https://example.test/source",
            observed_at="2026-09-21T00:00:00+00:00", geography="MA", metric="approximate search traffic",
            value=1000, unit="searches", is_proxy=True, confidence=0.7,
        )
        for query, expected in cases.items():
            report = market.build_report(query, "MA", [signal])
            self.assertEqual(report["market_category"], expected)
            self.assertEqual(report["handoff"][f"{expected}_spider"], [])
            candidate = report["handoff"]["category_candidates_requiring_data"][0]
            self.assertFalse(candidate["category_scorecard"]["eligible"])
            self.assertIsNone(candidate["category_scorecard"]["category_score"])
            self.assertEqual(candidate["profit_evidence_gate"]["decision"], "no-go")
            self.assertFalse(candidate["profit_evidence_gate"]["profit_guaranteed"])
            self.assertIn("margin_potential", candidate["profit_evidence_gate"]["missing_required_data"])
            self.assertIn("production_cost", candidate["profit_evidence_gate"]["missing_required_data"])

    def test_new_category_gates_are_specific_and_no_go_without_evidence(self):
        signal = market.Signal(
            product="Creative idea", source_name="fixture", source_url="https://example.test/source",
            observed_at="2026-09-21T00:00:00+00:00", geography="MA", metric="approximate search traffic",
            value=5000, unit="searches", is_proxy=True, confidence=0.7,
        )
        expected = {
            "sticker": {"format_printability", "licensing_risk"},
            "logo": {"originality_review", "similarity_review", "trademark_ip_risk"},
            "children_coloring_book": {"age_band", "print_economics", "child_safety", "illustration_rights_risk"},
            "illustrated_story": {"age_band", "illustration_rights_risk", "user_supplied_topic", "user_supplied_message"},
        }
        for category, required_missing in expected.items():
            report = market.build_report(category, "MA", [signal], market_category=category)
            candidate = report["handoff"]["category_candidates_requiring_data"][0]
            self.assertEqual(candidate["profit_evidence_gate"]["decision"], "no-go")
            self.assertTrue(required_missing.issubset(set(candidate["category_scorecard"]["missing_required_data"])))
            self.assertEqual(report["handoff"][f"{category}_spider"], [])
        logo_report = market.build_report("logo", "MA", [signal], market_category="logo")
        self.assertIn("never a trademark clearance claim", logo_report["handoff"]["logo_policy"])
        story_report = market.build_report("illustrated story", "MA", [signal], market_category="illustrated_story")
        self.assertIn("must come from the user", story_report["handoff"]["illustrated_story_policy"])

    def test_ebook_uses_books_fixture_and_separate_handoff(self):
        report = market.research_market("ebook budgeting", "MA", fixture_fetch, market_category="ebook")
        book_signals = [signal for signal in report["signals"] if signal["source_name"] == "Google Books public catalog"]
        self.assertTrue(book_signals)
        self.assertEqual(book_signals[0]["price"], 4.99)
        self.assertTrue(book_signals[0]["is_proxy"])
        self.assertIn("not verified demand or sales", " ".join(book_signals[0]["limitations"]))
        self.assertNotIn("digital_products_spider", report["handoff"])
        self.assertIn("ebook_spider", report["handoff"])

    def test_non_app_categories_do_not_call_apple(self):
        urls = []
        def tracking_fetch(url, **kwargs):
            urls.append(url)
            return fixture_fetch(url, **kwargs)
        market.research_market("تابلوات مرسومة ديكور", "MA", tracking_fetch, market_category="wall_art_decor")
        self.assertFalse(any("apple.com" in url for url in urls))
        self.assertTrue(any("trends.google.com" in url for url in urls))

    def test_weak_profit_proxy_is_no_go_even_with_other_fields_missing(self):
        signal = market.Signal(
            product="Weak signal", source_name="fixture", source_url="https://example.test/weak",
            observed_at="2026-09-21T00:00:00+00:00", geography="US", metric="approximate search traffic",
            value=1, unit="searches", is_proxy=True, confidence=0.5,
        )
        gate = market._profit_evidence_gate(signal, "digital_product")
        self.assertEqual(gate["decision"], "no-go")
        self.assertTrue(any("below" in reason for reason in gate["reasons"]))
        self.assertFalse(gate["profit_guaranteed"])

    def test_throttling_stops_without_retry(self):
        calls = []
        def throttled(url, **kwargs):
            calls.append(url)
            response = FakeResponse(b"")
            response.status_code = 429
            return response
        with self.assertRaises(market.SourceUnavailable):
            market.google_trends_signals("AI", "US", throttled)
        self.assertEqual(len(calls), 1)

class BossRouteTests(TestCase):
    def test_market_route_is_read_only_and_returns_handoff(self):
        import boss_spider
        fixture_report = market.build_report("AI photo", "US", [market.Signal(
            product="AI Photo Studio", source_name="fixture", source_url="https://example.test/source",
            observed_at="2026-09-21T00:00:00+00:00", geography="US", metric="chart rank",
            value=2, unit="rank", is_proxy=True, confidence=0.8,
            limitations=("fixture proxy",),
        )])
        with patch.object(boss_spider, "research_market", return_value=fixture_report), patch.object(boss_spider, "log_operation"):
            result = boss_spider._run_market_intelligence({"query": "AI photo", "geography": "US"}, "unused")
        self.assertTrue(result["success"])
        self.assertFalse(result["data"]["handoff"]["execution_allowed"])
        self.assertEqual(result["data"]["handoff"]["affiliate_spider"], [])
        self.assertIn("https://example.test/source", result["message"])
