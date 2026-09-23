import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from connectors import aliexpress_connector as ae
from connectors import fx
import market_spy_spider as market

FIXTURES = Path(__file__).parent
FAKE_ENV = {"ALIEXPRESS_APP_KEY": "123456", "ALIEXPRESS_APP_SECRET": "fake-secret-for-tests", "ALIEXPRESS_TRACKING_ID": "test",
            "MARKET_SPY_FX_OVERRIDE": "USD:MAD=10.0"}


class FakeResponse:
    status_code = 200
    def __init__(self, content):
        self.content = content


def ae_fetch(url, **_kwargs):
    assert "api-sg.aliexpress.com" in url
    return FakeResponse((FIXTURES / "fixtures_aliexpress_hot.json").read_bytes())


class ConnectorTests(TestCase):
    def test_signature_is_deterministic_hmac_sha256_uppercase(self):
        creds = ae.Credentials("123456", "secret")
        url = ae.build_request_url(ae.HOT_PRODUCTS_METHOD, {"ship_to_country": "MA"}, creds, timestamp_ms=1700000000000)
        params = {"app_key": "123456", "method": ae.HOT_PRODUCTS_METHOD, "sign_method": "sha256",
                  "timestamp": "1700000000000", "ship_to_country": "MA"}
        expected = ae.sign(params, "secret")
        self.assertIn(f"sign={expected}", url)
        self.assertEqual(expected, expected.upper())
        self.assertEqual(len(expected), 64)
        self.assertNotIn("secret", url)

    def test_credentials_only_from_env_and_never_repr_secret(self):
        with patch.dict(os.environ, {"ALIEXPRESS_APP_KEY": "", "ALIEXPRESS_APP_SECRET": ""}):
            self.assertFalse(ae.is_configured())
            with self.assertRaises(ae.AliExpressConfigError):
                ae.Credentials.from_env()
        with patch.dict(os.environ, FAKE_ENV):
            creds = ae.Credentials.from_env()
            self.assertNotIn("fake-secret", repr(creds))

    def test_parse_products_fields(self):
        products = ae.parse_products(json.loads((FIXTURES / "fixtures_aliexpress_hot.json").read_text()))
        self.assertEqual(len(products), 3)
        first = products[0]
        self.assertEqual(first.sale_price, 12.5)
        self.assertEqual(first.volume_30d, 5400)
        self.assertEqual(first.rating_percent, 96.5)
        self.assertEqual(first.commission_rate, 9.0)  # hot commission wins
        self.assertEqual(first.affiliate_link, "https://s.click.aliexpress.com/e/_mock1")
        self.assertIsNone(products[2].commission_rate)

    def test_api_error_raises(self):
        with self.assertRaises(ae.AliExpressAPIError):
            ae.parse_products({"error_response": {"code": "InvalidAppKey", "msg": "bad key"}})

    def test_fx_override_and_convert(self):
        with patch.dict(os.environ, {"MARKET_SPY_FX_OVERRIDE": "USD:MAD=10.0"}):
            rate = fx.get_rate("usd", "mad", lambda u, k: b"{}")
        self.assertEqual(fx.convert(12.5, rate), 125.0)
        self.assertEqual(fx.get_rate("MAD", "MAD", lambda u, k: b"").value, 1.0)


class MarketSpyAliExpressTests(TestCase):
    def setUp(self):
        p = patch.object(market, "CACHE_DIR", Path("/tmp/market-spy-ae-test-cache"))
        p.start(); self.addCleanup(p.stop)
        for path in market.CACHE_DIR.glob("*") if market.CACHE_DIR.exists() else []:
            path.unlink()

    def test_top_n_without_credentials_reports_missing_source(self):
        with patch.dict(os.environ, {"ALIEXPRESS_APP_KEY": "", "ALIEXPRESS_APP_SECRET": ""}):
            report = market.research_market("", "MA", ae_fetch, top_n=10)
        self.assertEqual(report["opportunities"], [])
        self.assertTrue(any("credentials" in e for e in report["source_errors"]))

    def test_top_n_mode_uses_real_commission_risk_and_mad(self):
        with patch.dict(os.environ, FAKE_ENV):
            report = market.research_market("", "MA", ae_fetch, top_n=2)
        self.assertEqual(report["mode"], "top_n_per_geography")
        self.assertLessEqual(len(report["opportunities"]), 2)
        top = report["opportunities"][0]
        self.assertEqual(top["product"], "Mock Wireless Earbuds")
        self.assertEqual(top["price_mad"], 125.0)
        self.assertEqual(top["commission_rate_percent"], 9.0)
        self.assertTrue(top["affiliate_scorecard"]["eligible"])
        self.assertEqual(top["affiliate_link"], "https://s.click.aliexpress.com/e/_mock1")
        self.assertIn("MAD", market.format_report(report))

    def test_top_products_by_geography(self):
        with patch.dict(os.environ, FAKE_ENV):
            result = market.top_products_by_geography(["ma", "fr"], n=3, fetcher=ae_fetch)
        self.assertEqual(set(result), {"MA", "FR"})


class BossTopNRouteTests(TestCase):
    def test_boss_passes_top_n(self):
        import boss_spider
        captured = {}
        def fake_research(query, geography, market_category=None, top_n=None, **_):
            captured.update(query=query, geography=geography, top_n=top_n)
            return market.build_report(query, geography, [], ["aliexpress: not configured"], "physical_product")
        with patch.object(boss_spider, "research_market", fake_research), patch.object(boss_spider, "log_operation", lambda *a, **k: None):
            result = boss_spider._run_market_intelligence({"geography": "ma", "top_n": 10}, "top 10 morocco")
        self.assertTrue(result["success"])
        self.assertEqual(captured, {"query": "", "geography": "MA", "top_n": 10})
