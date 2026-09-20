"""
webhook_server.py — استقبال الدفع وتسليم الملف تلقائياً
------------------------------------------------------------
خادم Flask صغير كيستقبل webhook ديال Shopify (orders/paid)، كيتحقق من
التوقيع (HMAC) باش نتأكدو أن الطلب جاي فعلاً من Shopify، وكيصيفط للزبون
رابط تحميل المنتج الرقمي عبر Gmail أوتوماتيكياً.

النشر (Deploy):
  يخدم على أي منصة كتدعم Python (Render.com / Railway.app فيهم Free Tier).
  1. push هاد الملف + requirements.txt لريبو GitHub
  2. فـ Render: New > Web Service > اختار الريبو
     Start command: gunicorn webhook_server:app
  3. زيد فـ Environment Variables:
       SHOPIFY_WEBHOOK_SECRET, SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_TOKEN,
       GMAIL_USER, GMAIL_APP_PASSWORD
  4. من بعد ما يطلع الرابط (مثلاً https://spider-webhook.onrender.com):
     فـ Shopify Admin > Settings > Notifications > Webhooks
     زيد webhook جديد: Event = "Order payment", URL = https://spider-webhook.onrender.com/webhook/orders-paid
"""

import os
import hmac
import hashlib
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, abort

from shopify_publish import get_download_url_for_product

app = Flask(__name__)

WEBHOOK_SECRET = os.environ["SHOPIFY_WEBHOOK_SECRET"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]


def verify_webhook(data: bytes, hmac_header: str) -> bool:
    """يتحقق أن الطلب جاي فعلاً من Shopify (وماشي من أي حد آخر كيحاول يزيف طلب دفع)."""
    digest = hmac.new(WEBHOOK_SECRET.encode("utf-8"), data, hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed_hmac, hmac_header or "")


def send_download_email(to_email: str, customer_name: str, items: list) -> None:
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "رابط تحميل طلبك 🕷️"

    lines = [f"مرحباً {customer_name}،", "", "شكراً على شرائك! هاذو روابط التحميل ديال المنتجات:"]
    for item in items:
        lines.append(f"- {item['title']}: {item['download_url']}")
    lines.append("")
    lines.append("إذا واجهت أي مشكل فالتحميل، رد على هاد الإيميل.")

    msg.attach(MIMEText("\n".join(lines), "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


@app.route("/webhook/orders-paid", methods=["POST"])
def orders_paid():
    raw_body = request.get_data()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")

    if not verify_webhook(raw_body, hmac_header):
        abort(401, description="توقيع غير صحيح — الطلب مرفوض.")

    order = request.get_json()
    customer_email = order.get("email") or order.get("contact_email")
    customer_name = (order.get("customer") or {}).get("first_name", "صديقنا")

    items = []
    for line_item in order.get("line_items", []):
        product_id = line_item.get("product_id")
        download_url = get_download_url_for_product(product_id) if product_id else None
        if download_url:
            items.append({"title": line_item.get("title", ""), "download_url": download_url})

    if customer_email and items:
        try:
            send_download_email(customer_email, customer_name, items)
        except Exception as e:
            # نرجعو 200 لـ Shopify حتى لو طاح الإيميل، باش ما يعاودش يصيفط نفس
            # الطلب مرات بزاف — لكن نسجلو الخطأ فالـ logs باش نشوفوه
            app.logger.error(f"فشل إرسال الإيميل: {e}")

    return {"status": "received"}, 200


@app.route("/", methods=["GET"])
def health_check():
    return {"status": "spider webhook server is running"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
