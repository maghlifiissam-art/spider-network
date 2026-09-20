"""
shopify_publish.py — نشر تلقائي للمنتجات الرقمية على Shopify
----------------------------------------------------------------
كيفاش كيخدم:
1. الكتاب/المنتج المولّد (من book_spider.py مثلاً) كيتحفظ كملف داخل الريبو
   (نفس منطق data/spider_log.json ديال monitor_spider.py) — GitHub Actions
   كيدير commit للملف، وكيبقى متاح عبر رابط عام:
   https://raw.githubusercontent.com/<user>/<repo>/main/<path>
2. هاد السكريبت كياخذ هاد الرابط + العنوان + الوصف + الثمن، وكيصاوب بيهم
   منتج جديد فـ Shopify عبر Admin API (بدون تسجيل يدوي فكل مرة).
3. الملف الرقمي كيتسلّم من بعد عبر webhook_server.py ملي يتم الدفع.

المتطلبات (Secrets):
  SHOPIFY_STORE_DOMAIN   -> مثال: my-store.myshopify.com
  SHOPIFY_ADMIN_TOKEN    -> Admin API access token (من صفحة Apps > Develop apps)
"""

import os
import requests

STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "")
ADMIN_TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
API_VERSION = "2024-10"


def _base_url() -> str:
    return f"https://{STORE_DOMAIN}/admin/api/{API_VERSION}"


def _headers() -> dict:
    return {
        "X-Shopify-Access-Token": ADMIN_TOKEN,
        "Content-Type": "application/json",
    }


def create_digital_product(title: str, description_html: str, price: str,
                            download_url: str, product_type: str = "Digital Book") -> dict:
    """
    كيصاوب منتج جديد فـ Shopify. رابط التحميل (download_url) كنخزنوه فـ
    metafield خاص باش webhook_server.py يقدر يجيبو ملي يوصل طلب الدفع.

    يرجع dict فيه نتيجة العملية: {"success": bool, "product_id": int|None, "error": str|None}
    """
    if not STORE_DOMAIN or not ADMIN_TOKEN:
        return {"success": False, "product_id": None, "error": "SHOPIFY_STORE_DOMAIN أو SHOPIFY_ADMIN_TOKEN ناقصين."}

    payload = {
        "product": {
            "title": title,
            "body_html": description_html,
            "product_type": product_type,
            "status": "active",
            "variants": [{"price": price, "requires_shipping": False, "inventory_management": None}],
        }
    }

    try:
        resp = requests.post(f"{_base_url()}/products.json", json=payload, headers=_headers(), timeout=30)
        resp.raise_for_status()
        product = resp.json()["product"]
        product_id = product["id"]

        # تخزين رابط التحميل فـ metafield خاص بالمنتج (باش يستعملو webhook_server.py من بعد)
        metafield_payload = {
            "metafield": {
                "namespace": "spider_network",
                "key": "download_url",
                "value": download_url,
                "type": "single_line_text_field",
            }
        }
        requests.post(
            f"{_base_url()}/products/{product_id}/metafields.json",
            json=metafield_payload,
            headers=_headers(),
            timeout=30,
        )

        return {"success": True, "product_id": product_id, "error": None}

    except requests.exceptions.RequestException as e:
        return {"success": False, "product_id": None, "error": str(e)}


def get_download_url_for_product(product_id: int) -> str | None:
    """كيرجع رابط التحميل المخزن فـ metafield ديال المنتج (كيستعملها webhook_server.py)."""
    try:
        resp = requests.get(
            f"{_base_url()}/products/{product_id}/metafields.json",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        for mf in resp.json().get("metafields", []):
            if mf["namespace"] == "spider_network" and mf["key"] == "download_url":
                return mf["value"]
    except requests.exceptions.RequestException:
        pass
    return None
