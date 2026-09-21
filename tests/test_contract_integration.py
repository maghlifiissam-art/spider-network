import unittest
from datetime import datetime, timezone

from bullet_spider import MarketSpyHandoffAdapter, OfflineFixtureAdapter, run_bullet_spider
import market_spy_spider as market


def complete_row(category):
    components = {
        "rights_risk": 80, "fulfillment_risk": 80, "format_printability": 90,
        "licensing_risk": 90, "originality_review": 90, "similarity_review": 90,
        "trademark_ip_risk": 85, "age_band": 90, "print_economics": 85,
        "child_safety": 95, "illustration_rights_risk": 90,
        "user_supplied_topic": 100, "user_supplied_message": 100,
    }
    return {
        "opportunity_id": "spy-" + category,
        "product": "شراء " + category,
        "market_category": category,
        "geography": "MA",
        "observed_at": "2026-09-21T00:00:00Z",
        "source_urls": ["https://example.test/public"],
        "metric_or_proxy": "purchase_intent_proxy",
        "opportunity_score": 82,
        "confidence": .8,
        "limitations": ["offline contract fixture"],
        "category_scorecard": {"eligible": True, "components": components},
        "profit_evidence_gate": {"decision": "go", "evidence": {
            "competition": 70, "price": 12, "margin_potential": 75,
            "production_cost": 2, "production_time": 10, "confidence": 80,
        }},
        "previous_value": 50, "price": 12, "currency": "USD",
        "production_cost": 2, "production_time_hours": 10,
        "price_margin": .75, "competition": .3, "risk": .1,
        "supply_gap": .8, "producibility": .9,
    }


class ContractTests(unittest.TestCase):
    def test_versioned_envelope_preserves_no_go(self):
        row = complete_row("logo")
        row["profit_evidence_gate"]["decision"] = "no-go"
        env = {"handoff": {"schema_version": "market_spy_handoff.v1", "execution_allowed": False, "logo_spider": [row]}}
        result = run_bullet_spider({"as_of": "2026-09-21T01:00:00Z"}, [MarketSpyHandoffAdapter(env)])
        self.assertEqual(result["opportunities"][0]["decision"], "no_go")
        self.assertEqual(result["briefs"], [])
        self.assertEqual(result["opportunities"][0]["observed_at"], row["observed_at"])
        self.assertEqual(result["opportunities"][0]["profit_evidence_gate"]["decision"], "no-go")

    def test_all_categories_map_and_route(self):
        routes = {
            "ebook": "book_spider", "design_asset": "visual_spider",
            "wall_art_decor": "wall_art_decor_spider", "sticker": "sticker_spider",
            "logo": "logo_spider", "children_coloring_book": "children_coloring_book_spider",
            "illustrated_story": "illustrated_story_spider", "physical_product": "physical_product_spider",
        }
        for source_category, spider in routes.items():
            row = complete_row(source_category)
            result = run_bullet_spider({"as_of": "2026-09-21T01:00:00Z"}, [OfflineFixtureAdapter([row])])
            self.assertEqual(result["opportunities"][0]["decision"], "go", source_category)
            self.assertIn(spider, result["briefs"][0]["assigned_spiders"])

    def test_story_user_gates_and_category_safety(self):
        for category, missing_key in [("illustrated_story", "user_supplied_message"), ("logo", "trademark_ip_risk"), ("children_coloring_book", "child_safety"), ("sticker", "format_printability")]:
            row = complete_row(category)
            row["category_scorecard"]["components"].pop(missing_key)
            result = run_bullet_spider({"as_of": "2026-09-21T01:00:00Z"}, [OfflineFixtureAdapter([row])])
            self.assertEqual(result["opportunities"][0]["decision"], "no_go")
            self.assertEqual(result["briefs"], [])

    def test_envelope_requires_version_and_explicit_execution_block(self):
        with self.assertRaises(ValueError):
            MarketSpyHandoffAdapter({"handoff": {}})
