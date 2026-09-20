"""
whatsapp_bot.py — بوت واتساب للبيع الأوتوماتيكي (متعدد اللغات)
------------------------------------------------------------------
كيستعمل WhatsApp Business Cloud API الرسمي ديال Meta (ماشي مكتبة غير
رسمية) — هذا مهم: أي حل غير رسمي (بحال whatsapp-web.js) كيخالف شروط
واتساب وممكن يوصل لحظر الرقم نهائياً.

الإعداد (مرة وحدة، عبر developers.facebook.com):
  1. صاوب Meta App من نوع "Business" وزيد منتج "WhatsApp"
  2. جيب رقم تجريبي مجاني (test number) للتجربة، ولا رقمك الخاص للإنتاج
  3. من الإعدادات، خزن:
       WHATSAPP_ACCESS_TOKEN     -> التوكن المؤقت/الدائم
       WHATSAPP_PHONE_NUMBER_ID  -> رقم الهاتف ديال البزنس
       WHATSAPP_VERIFY_TOKEN     -> كلمة سر تختارها نتا لتفعيل الـ webhook
  4. ملي تنشر هاد السكريبت (Render/Replit)، سجل الـ Webhook فـ Meta:
       Callback URL: https://<رابطك>/webhook
       Verify Token: نفس WHATSAPP_VERIFY_TOKEN
       Subscribe to: messages

⚠️ حدود مهمة:
  - الرقم التجريبي المجاني كيقدر يصيفط غير لعدد محدود من الأرقام المسجلة
    مسبقاً (Recipients) — ماشي جاهز للعموم حتى تدير Verification/رقم حقيقي
  - إيلا الزبون ماردش من 24 ساعة، ما تقدرش تبدا محادثة جديدة بلا "Template
    Message" معتمد من Meta (سياسة عامة ديال واتساب، ماشي تقييد ديالنا)
"""

import os
import requests
from flask import Flask, request

from groq import Groq
from catalog import search_catalog

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
MODEL = "llama-3.1-8b-instant"

client = Groq(api_key=GROQ_API_KEY)


def send_whatsapp_message(to: str, text: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    resp = requests.post(GRAPH_API_URL, json=payload, headers=headers, timeout=20)
    if not resp.ok:
        app.logger.error(f"فشل إرسال رسالة واتساب: {resp.status_code} {resp.text}")


def generate_sales_reply(customer_message: str) -> str:
    """
    كيدير بحث فالفهرس الحقيقي، ومن بعد كيولد جواب مبني عليه فقط
    (بلا اختلاق منتجات ما كاينينش).
    """
    matches = search_catalog(customer_message, max_results=3)

    if matches:
        products_text = "\n".join(
            f"- {p['name']} ({p['price_cents']/100:.2f}$): {p['buy_link']}" for p in matches
        )
    else:
        products_text = "لا توجد منتجات مطابقة حالياً فالفهرس."

    system_prompt = """You are a friendly, helpful sales assistant for a small digital-products \
store. Detect the customer's language and reply in the SAME language. Recommend ONLY the \
products listed below — never invent a product, price, or link that isn't listed. If nothing \
matches, politely say so and ask what they're looking for. Keep replies short and warm, like a \
real WhatsApp conversation, not a formal email."""

    user_prompt = f"Available matching products:\n{products_text}\n\nCustomer message: {customer_message}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "عذراً، صرا مشكل تقني. عاود المحاولة من بعد شوية. 🙏"


# ---------------------------------------------------------------------------
# تفعيل الـ Webhook (Meta كتصيفط GET مرة وحدة للتحقق)
# ---------------------------------------------------------------------------
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


# ---------------------------------------------------------------------------
# استقبال الرسائل الجايين من الزبناء
# ---------------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages")
        if not messages:
            return {"status": "no_message"}, 200  # كايناين إشعارات أخرى (statuses) كنتجاهلوها

        message = messages[0]
        sender = message["from"]
        text = message.get("text", {}).get("body", "")

        if text:
            reply = generate_sales_reply(text)
            send_whatsapp_message(sender, reply)

    except (KeyError, IndexError, TypeError) as e:
        app.logger.error(f"شكل بيانات غير متوقع: {e}")

    return {"status": "received"}, 200


@app.route("/", methods=["GET"])
def health_check():
    return {"status": "whatsapp bot is running"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
