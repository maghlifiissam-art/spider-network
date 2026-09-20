"""
auto_publish_visual.py — من الفكرة إلى ملصق/شعار جاهز للبيع
------------------------------------------------------------------
يكمل خط visual_spider.py: كيولد ملصق أو شعار، ومن بعد كينشرو مباشرة
كمنتج رقمي قابل للبيع على Gumroad (نفس منطق الكتب وكتب التلوين).

متغيرات البيئة:
  GUMROAD_ACCESS_TOKEN     (إلزامي)
  POLLINATIONS_TOKEN       (اختياري)
  VISUAL_TYPE              "poster" أو "logo"
  VISUAL_TOPIC             (للملصق) موضوع/نص الملصق
  VISUAL_STYLE             (للملصق) الستايل (افتراضي: "modern minimal")
  VISUAL_BRAND_NAME        (للشعار) اسم البراند
  VISUAL_STYLE_KEYWORDS    (للشعار) كلمات ستايل إضافية
  VISUAL_PRICE_CENTS       (افتراضي: 200 = $2.00)
"""

import os
from visual_spider import generate_poster, generate_logo
from gumroad_publish import publish_book
from catalog import add_product
from ops_log import log_operation


def main():
    visual_type = os.environ["VISUAL_TYPE"]
    price_cents = int(os.environ.get("VISUAL_PRICE_CENTS", "200"))
    output_dir = "generated_visuals"
    os.makedirs(output_dir, exist_ok=True)

    if visual_type == "poster":
        topic = os.environ["VISUAL_TOPIC"]
        style = os.environ.get("VISUAL_STYLE", "modern minimal")
        output_path = os.path.join(output_dir, "poster.jpg")
        print(f"🎨 كنولدو ملصق: {topic} ({style})")
        result = generate_poster(topic, style, output_path)
        product_name = f"ملصق رقمي: {topic}"
        description = f"<p>ملصق رقمي جاهز للطباعة — {topic}، ستايل: {style}</p>"

    elif visual_type == "logo":
        brand_name = os.environ["VISUAL_BRAND_NAME"]
        style_keywords = os.environ.get("VISUAL_STYLE_KEYWORDS", "clean, professional")
        output_path = os.path.join(output_dir, "logo.jpg")
        print(f"🎨 كنولدو شعار: {brand_name}")
        result = generate_logo(brand_name, style_keywords, output_path)
        product_name = f"شعار: {brand_name}"
        description = f"<p>شعار رقمي جاهز — {brand_name}</p>"

    else:
        raise SystemExit("❌ VISUAL_TYPE خاصو يكون 'poster' ولا 'logo'.")

    if not result["success"]:
        raise SystemExit(f"❌ فشل توليد الصورة: {result['error']}")

    print("🚀 كننشرو على Gumroad...")
    publish_result = publish_book(
        file_path=output_path,
        name=product_name,
        price_cents=price_cents,
        description_html=description,
        native_type="digital",
    )

    if publish_result["success"]:
        print(f"✅ تم النشر بنجاح! رابط الشراء: {publish_result['buy_link']}")
        add_product(product_name, publish_result["buy_link"], price_cents, visual_type)
        log_operation(visual_type, "success", message=publish_result["buy_link"], product_name=product_name)
    else:
        log_operation(visual_type, "failed", message=publish_result["error"], product_name=product_name)
        raise SystemExit(f"❌ فشل النشر: {publish_result['error']}")


if __name__ == "__main__":
    main()
