import unittest
from datetime import date
from unittest.mock import patch

import demand_pipeline as pipeline


class WikimediaResponse:
    status_code = 200
    def json(self):
        return {"items": [{"views": i + 1} for i in range(14)]}


class DemandPipelineTests(unittest.TestCase):
    def test_global_readership_is_proxy_not_local_demand(self):
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            return WikimediaResponse()
        signal = pipeline.wikipedia_readership("Employment_law", fetch=fetch, today=date(2026, 9, 29))
        self.assertEqual(signal.geography, "global")
        self.assertTrue(signal.is_proxy)
        self.assertEqual(signal.value, sum(range(8, 15)))
        self.assertIn("/20260914/20260927", calls[0][0])
        self.assertIn("SpiderNetwork", calls[0][1]["headers"]["User-Agent"])

    @patch.object(pipeline, "google_trends_signals", return_value=[])
    @patch.object(pipeline, "wikipedia_readership")
    def test_no_ungrounded_brief_from_readership(self, reader, _trends):
        reader.return_value = pipeline.Signal(
            "Employment law", "Wikimedia", "https://wikimedia.org/example", "2026-09-29T09:00:00Z",
            "global", "article views", 100, "views", True, 0.45)
        result = pipeline.run("US", themes=(("employment law", "ebook", "Employment_law"),))
        row = result["themes"][0]
        self.assertEqual(row["draft_briefs"], [])
        self.assertEqual(row["bullet_assessments"][0]["decision"], "no_go")
        self.assertEqual(row["ranked_research_candidates"][0]["geography"], "global")

    def test_invalid_geography_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.run("United States")
