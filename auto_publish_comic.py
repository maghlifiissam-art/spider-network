"""
auto_publish_comic.py — من البروبت أو السيناريو إلى قصة مصورة جاهزة للبيع
----------------------------------------------------------------------------
COMIC_MODE = "prompt" -> يستعمل COMIC_TOPIC (فكرة عامة، الوكيل يبني القصة)
COMIC_MODE = "script" -> يستعمل COMIC_USER_SCRIPT (سيناريو كامل من المستخدم)

متغيرات البيئة:
  GROQ_API_KEY, GUMROAD_ACCESS_TOKEN     (إلزاميين)
  POLLINATIONS_TOKEN                      (اختياري)
  COMIC_MODE            "prompt" أو "script"
  COMIC_TOPIC           (إلزامي إيلا mode=prompt)
  COMIC_USER_SCRIPT      (إلزامي إيلا mode=script)
  COMIC_LANGUAGE        (افتراضي: "العربية")
  COMIC_PANELS          (افتراضي: 10)
  COMIC_PRICE_CENTS     (افتراضي: 400 = $4.00)
"""

import os
import re
from groq import Groq

from comic_spider import generate_comic_script
from compile_comic_pdf import generate_panel_images, compile_comic_to_pdf
from gumroad_publish import publish_book
from catalog import add_product
from ops_log import log_operation


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:60] or "comic"


def main():
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    mode = os.environ.get("COMIC_MODE", "prompt")
    language = os.environ.get("COMIC_LANGUAGE", "العربية")
    panels_count = int(os.environ.get("COMIC_PANELS", "10"))
    price_cents = int(os.environ.get("COMIC_PRICE_CENTS", "400"))
    topic = os.environ.get("COMIC_TOPIC", "")
    user_script = os.environ.get("COMIC_USER_SCRIPT", "")

    print("📝 كنبنيو السيناريو...")
    script = generate_comic_script(client, language, panels_count, mode, topic, user_script)
    if "error" in script:
        raise SystemExit(f"❌ فشل بناء السيناريو: {script['error']}")

    title = script.get("title", topic or "قصة مصورة")
    panels = script["panels"]
    print(f"  → العنوان: {title} ({len(panels)} لوحة)")

    output_dir = f"generated_comics/{slugify(title)}"
    print("🎨 كنولدو الصور (كل لوحة ~15 ثانية)...")
    images_result = generate_panel_images(panels, output_dir)
    if images_result["errors"]:
        print("⚠️ بعض اللوحات فشلات:", images_result["errors"])
    if not images_result["success"]:
        raise SystemExit("❌ فشل توليد الصور بالكامل.")

    pdf_path = os.path.join(output_dir, "comic.pdf")
    print("📄 كنجمعو القصة المصورة فـ PDF...")
    pdf_result = compile_comic_to_pdf(panels, images_result["image_paths"], pdf_path, language)
    if not pdf_result["success"]:
        raise SystemExit(f"❌ فشل تجميع PDF: {pdf_result['error']}")

    print("🚀 كننشرو على Gumroad...")
    publish_result = publish_book(
        file_path=pdf_path,
        name=title,
        price_cents=price_cents,
        description_html=f"<p>قصة مصورة رقمية — {title} ({len(panels)} لوحة)</p>",
        native_type="digital",
    )

    if publish_result["success"]:
        print(f"✅ تم النشر بنجاح! رابط الشراء: {publish_result['buy_link']}")
        add_product(title, publish_result["buy_link"], price_cents, "comic", description=topic or user_script[:200])
        log_operation("comic", "success", message=publish_result["buy_link"], product_name=title)
    else:
        log_operation("comic", "failed", message=publish_result["error"], product_name=title)
        raise SystemExit(f"❌ فشل النشر: {publish_result['error']}")


if __name__ == "__main__":
    main()
