"""
catalog.py — فهرس المنتجات المشترك
------------------------------------------------------------------
كل سكريبت نشر (auto_publish_book.py, auto_publish_comic.py,
auto_publish_coloring_book.py, auto_publish_visual.py) كيسجل فيه أي
منتج جديد كينشر بنجاح على Gumroad. بوت واتساب (whatsapp_bot.py) كيقرا
من هاد الفهرس باش يقترح على الزبون منتجات حقيقية فقط (بلا اختلاق).

الملف كيتسجل فـ data/product_catalog.json ويبقى فالريبو (نفس منطق
data/spider_log.json ديال monitor_spider.py).
"""

import os
import json
from datetime import datetime, timezone

CATALOG_PATH = "data/product_catalog.json"


def load_catalog() -> list:
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def add_product(name: str, buy_link: str, price_cents: int, product_type: str, description: str = "") -> None:
    """
    product_type: "book" / "comic" / "coloring_book" / "poster" / "logo"
    """
    catalog = load_catalog()
    catalog.append(
        {
            "name": name,
            "buy_link": buy_link,
            "price_cents": price_cents,
            "type": product_type,
            "description": description,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def search_catalog(query: str, max_results: int = 5) -> list:
    """بحث بسيط بالكلمات المفتاحية فأسماء وأوصاف المنتجات (بلا أي API خارجي)."""
    query_words = query.lower().split()
    catalog = load_catalog()

    def score(product: dict) -> int:
        text = f"{product['name']} {product.get('description', '')}".lower()
        return sum(1 for w in query_words if w in text)

    scored = [(score(p), p) for p in catalog]
    scored = [sp for sp in scored if sp[0] > 0]
    scored.sort(key=lambda sp: sp[0], reverse=True)
    return [p for _, p in scored[:max_results]]
