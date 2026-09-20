import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import catalog


class CatalogTests(TestCase):
    def test_add_and_search_catalog(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "products.json")
            with patch.object(catalog, "CATALOG_PATH", path):
                catalog.add_product(
                    "دليل التسويق بالعمولة",
                    "https://example.invalid/product",
                    500,
                    "book",
                    "دليل عملي للمبتدئين",
                )
                results = catalog.search_catalog("التسويق المبتدئين")
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["price_cents"], 500)
                saved = json.loads(Path(path).read_text(encoding="utf-8"))
                self.assertEqual(saved[0]["type"], "book")

    def test_search_ignores_unmatched_products(self):
        with patch.object(catalog, "load_catalog", return_value=[
            {"name": "Poster", "description": "Minimal wall art"},
        ]):
            self.assertEqual(catalog.search_catalog("book"), [])
