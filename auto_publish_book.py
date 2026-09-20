"""
auto_publish_book.py — من الفكرة إلى منتج جاهز للبيع، فخطوة وحدة
---------------------------------------------------------------------
كيقرا مواصفات الكتاب من متغيرات البيئة (كيوصلوها GitHub Actions inputs)،
كيولد الكتاب كامل عبر book_spider، كيحفظو كملف، ومن بعد كينشرو مباشرة
كمنتج جاهز للبيع على Gumroad عبر gumroad_publish.

متغيرات البيئة المطلوبة:
  GROQ_API_KEY, GUMROAD_ACCESS_TOKEN   -> المفاتيح
  BOOK_TOPIC                            -> موضوع الكتاب (إلزامي)
  BOOK_GENRE        (افتراضي: "دليل عملي / How-to")
  BOOK_LANGUAGE     (افتراضي: "العربية")
  BOOK_CHAPTERS     (افتراضي: 5)
  BOOK_PRICE_CENTS  (افتراضي: 500 = $5.00)

اختياري (لإشعار بالإيميل بعد النشر بنجاح):
  GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
"""

import os
import re
import smtplib
from email.mime.text import MIMEText

from groq import Groq
from book_spider import generate_full_book
from gumroad_publish import publish_book
from catalog import add_product
from ops_log import log_operation


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:60] or "book"


def notify_by_email(subject: str, body: str) -> None:
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)
    if not (gmail_user and gmail_pass):
        return  # الإشعار اختياري — إيلا ماكانش Gmail معطى، نتخطاو بلا خطأ

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg["Subject"] = subject
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipient, msg.as_string())


def main():
    groq_api_key = os.environ["GROQ_API_KEY"]
    topic = os.environ["BOOK_TOPIC"]
    genre = os.environ.get("BOOK_GENRE", "دليل عملي / How-to")
    language = os.environ.get("BOOK_LANGUAGE", "العربية")
    chapters_count = int(os.environ.get("BOOK_CHAPTERS", "5"))
    price_cents = int(os.environ.get("BOOK_PRICE_CENTS", "500"))

    client = Groq(api_key=groq_api_key)

    print(f"📖 كنولدو الكتاب: {topic}")
    final_text = ""
    book_title = topic
    for event_type, payload in generate_full_book(client, topic, genre, language, chapters_count):
        if event_type == "outline":
            book_title = payload.get("title", topic)
            print(f"  → العنوان: {book_title}")
        elif event_type == "chapter":
            print(f"  → فصل جاهز: {payload['chapter'].get('title')}")
        elif event_type == "done":
            final_text = payload

    os.makedirs("generated_books", exist_ok=True)
    file_path = f"generated_books/{slugify(book_title)}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_text)
    print(f"✅ الكتاب تسجل فـ {file_path}")

    print("🚀 كننشرو على Gumroad...")
    result = publish_book(
        file_path=file_path,
        name=book_title,
        price_cents=price_cents,
        description_html=f"<p>{book_title}</p>",
        native_type="ebook",
    )

    if result["success"]:
        msg = f"✅ تم النشر بنجاح!\nالكتاب: {book_title}\nرابط الشراء: {result['buy_link']}"
        print(msg)
        add_product(book_title, result["buy_link"], price_cents, "book", description=topic)
        log_operation("book", "success", message=result["buy_link"], product_name=book_title)
        notify_by_email(f"[Spider Network] كتاب جديد جاهز للبيع: {book_title}", msg)
    else:
        msg = f"❌ فشل النشر: {result['error']}"
        print(msg)
        log_operation("book", "failed", message=result["error"], product_name=book_title)
        notify_by_email(f"[Spider Network] فشل نشر كتاب: {book_title}", msg)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
