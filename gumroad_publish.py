"""
gumroad_publish.py — نشر تلقائي للمنتجات الرقمية على Gumroad
------------------------------------------------------------------
خبر مهم: Gumroad كيدير التسليم الأوتوماتيكي بنفسه بمجرد ما يكون الملف
مرفق بالمنتج والمنتج منشور — ما خاصناش webhook ولا سيرفر إيميل خاص بالتسليم
(بخلاف Shopify اللي كان خاصو حل مخصص). هذا كيبسط بزاف البنية.

هاد السكريبت كيدير 3 خطوات أوتوماتيكياً:
  1. رفع الملف (multipart/S3 flow ديال Gumroad)
  2. إنشاء المنتج (draft) وربطو بالملف المرفوع
  3. نشر المنتج (enable) — من هنا Gumroad كيتكلف بالبيع والتسليم بروحو

الإعداد (مرة وحدة، يدوي):
  1. سجل الدخول لـ Gumroad -> gumroad.com/settings/advanced#application-form
  2. سجل تطبيق OAuth، ودير "Generate access token"
  3. اختار الصلاحيات: edit_products (إلزامي)، view_sales (اختياري لتتبع المبيعات)
  4. خزن التوكن كـ GUMROAD_ACCESS_TOKEN (GitHub Secret مثلاً)
"""

import os
import requests

API_BASE = "https://api.gumroad.com/v2"
ACCESS_TOKEN = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB — نفس تقسيم Gumroad


def _auth_params(extra: dict | None = None) -> dict:
    params = {"access_token": ACCESS_TOKEN}
    if extra:
        params.update(extra)
    return params


# ---------------------------------------------------------------------------
# الخطوة 1: رفع الملف (presign -> upload parts -> complete)
# ---------------------------------------------------------------------------
def upload_file_to_gumroad(file_path: str) -> dict:
    """
    كيرفع ملف لـ Gumroad ويرجع dict: {"success": bool, "file_url": str|None, "error": str|None}
    """
    if not ACCESS_TOKEN:
        return {"success": False, "file_url": None, "error": "GUMROAD_ACCESS_TOKEN ناقص."}

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    try:
        # --- Presign ---
        presign_resp = requests.post(
            f"{API_BASE}/files/presign",
            data=_auth_params({"filename": filename, "file_size": file_size}),
            timeout=30,
        )
        presign_resp.raise_for_status()
        presign = presign_resp.json()
        if not presign.get("success", True) and "upload_id" not in presign:
            return {"success": False, "file_url": None, "error": presign.get("message", "فشل presign.")}

        upload_id = presign["upload_id"]
        key = presign["key"]
        canonical_file_url = presign["file_url"]
        parts_info = presign["parts"]

        # --- Upload each part ---
        uploaded_parts = []
        with open(file_path, "rb") as f:
            for part in parts_info:
                chunk = f.read(CHUNK_SIZE)
                put_resp = requests.put(part["presigned_url"], data=chunk, timeout=120)
                put_resp.raise_for_status()
                etag = put_resp.headers.get("ETag", "").strip('"')
                uploaded_parts.append({"part_number": part["part_number"], "etag": etag})

        # --- Complete (مرة وحدة فقط) ---
        complete_data = {"upload_id": upload_id, "key": key}
        for i, p in enumerate(uploaded_parts):
            complete_data[f"parts[{i}][part_number]"] = p["part_number"]
            complete_data[f"parts[{i}][etag]"] = p["etag"]

        complete_resp = requests.post(
            f"{API_BASE}/files/complete",
            data=_auth_params(complete_data),
            timeout=60,
        )
        complete_resp.raise_for_status()
        complete_json = complete_resp.json()

        return {"success": True, "file_url": complete_json.get("file_url", canonical_file_url), "error": None}

    except requests.exceptions.RequestException as e:
        return {"success": False, "file_url": None, "error": str(e)}


# ---------------------------------------------------------------------------
# الخطوة 2: إنشاء المنتج (draft) مربوط بالملف
# ---------------------------------------------------------------------------
def create_product(name: str, price_cents: int, file_url: str, description_html: str = "",
                    native_type: str = "ebook", currency: str = "usd") -> dict:
    """
    native_type: digital / course / ebook / membership / bundle ... (ثابت، ما يتبدلش من بعد)
    price_cents: الثمن بالسنتيم — 500 = $5.00
    """
    if not ACCESS_TOKEN:
        return {"success": False, "product_id": None, "short_url": None, "error": "GUMROAD_ACCESS_TOKEN ناقص."}

    data = {
        "native_type": native_type,
        "name": name,
        "price": price_cents,
        "price_currency_type": currency,
        "description": description_html,
        "files[][url]": file_url,
    }

    try:
        resp = requests.post(f"{API_BASE}/products", data=_auth_params(data), timeout=30)
        resp.raise_for_status()
        product = resp.json()["product"]
        return {"success": True, "product_id": product["id"], "short_url": product.get("short_url"), "error": None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "product_id": None, "short_url": None, "error": str(e)}


# ---------------------------------------------------------------------------
# الخطوة 3: نشر المنتج — من هنا كيولي البيع والتسليم أوتوماتيكي بالكامل
# ---------------------------------------------------------------------------
def publish_product(product_id: str) -> dict:
    try:
        resp = requests.put(f"{API_BASE}/products/{product_id}/enable", data=_auth_params(), timeout=30)
        resp.raise_for_status()
        return {"success": True, "error": None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# دالة شاملة: من الملف المحلي إلى منتج منشور وجاهز للبيع
# ---------------------------------------------------------------------------
def publish_book(file_path: str, name: str, price_cents: int, description_html: str = "",
                  native_type: str = "ebook") -> dict:
    """
    كتاخذ ملف الكتاب المولّد (من book_spider.py) وكتنشرو مباشرة كمنتج جاهز للبيع.
    ترجع dict: {"success": bool, "buy_link": str|None, "product_id": str|None, "error": str|None}
    """
    upload = upload_file_to_gumroad(file_path)
    if not upload["success"]:
        return {"success": False, "buy_link": None, "product_id": None, "error": f"فشل رفع الملف: {upload['error']}"}

    product = create_product(
        name=name,
        price_cents=price_cents,
        file_url=upload["file_url"],
        description_html=description_html,
        native_type=native_type,
    )
    if not product["success"]:
        return {"success": False, "buy_link": None, "product_id": None, "error": f"فشل إنشاء المنتج: {product['error']}"}

    publish = publish_product(product["product_id"])
    if not publish["success"]:
        return {
            "success": False,
            "buy_link": None,
            "product_id": product["product_id"],
            "error": f"تم إنشاء المنتج لكن فشل النشر: {publish['error']}",
        }

    return {"success": True, "buy_link": product["short_url"], "product_id": product["product_id"], "error": None}
