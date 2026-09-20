"""
auto_publish_coloring_book.py — من الفكرة إلى كتاب تلوين جاهز للبيع
------------------------------------------------------------------------
1. كيولد الصور (غلاف + صفحات) عبر visual_spider (Pollinations.ai)
2. كيجمعهم فـ PDF واحد عبر compile_pdf
3. كينشر الـ PDF كمنتج جاهز للبيع على Gumroad عبر gumroad_publish

⚠️ الوقت المتوقع: كل صورة كتاخذ ~15 ثانية (حد النسخة المجانية ديال
Pollinations)، فكتاب بـ 10 صفحات + غلاف = تقريباً 3 دقائق.

متغيرات البيئة:
  GUMROAD_ACCESS_TOKEN            (إلزامي)
  POLLINATIONS_TOKEN              (اختياري — لتفادي حد الـ 15 ثانية)
  COLORING_THEME                  مثال: "حيوانات الغابة"
  COLORING_PAGES     (افتراضي: 8)
  COLORING_PRICE_CENTS (افتراضي: 300 = $3.00)
"""

import os
from visual_spider import generate_coloring_book
from compile_pdf import compile_images_to_pdf
from gumroad_publish import publish_book
from catalog import add_product
from ops_log import log_operation


def main():
    theme = os.environ["COLORING_THEME"]
    pages_count = int(os.environ.get("COLORING_PAGES", "8"))
    price_cents = int(os.environ.get("COLORING_PRICE_CENTS", "300"))

    output_dir = f"generated_coloring_books/{theme.replace(' ', '_')}"
    print(f"🎨 كنولدو كتاب تلوين: {theme} ({pages_count} صفحات)")

    book_result = generate_coloring_book(theme, pages_count, output_dir)
    if book_result["errors"]:
        print("⚠️ بعض الصور فشلات:", book_result["errors"])
    if not book_result["success"]:
        raise SystemExit("❌ فشل توليد الصور بالكامل.")

    # ترتيب الصفحات: الغلاف أولاً، من بعد الصفحات بالترتيب
    image_paths = []
    if book_result["cover"]:
        image_paths.append(book_result["cover"])
    image_paths.extend(book_result["pages"])

    pdf_path = os.path.join(output_dir, "coloring_book.pdf")
    print("📄 كنجمعو الصور فـ PDF...")
    pdf_result = compile_images_to_pdf(image_paths, pdf_path)
    if not pdf_result["success"]:
        raise SystemExit(f"❌ فشل تجميع PDF: {pdf_result['error']}")

    print("🚀 كننشرو على Gumroad...")
    product_name = f"كتاب تلوين للأطفال: {theme}"
    publish_result = publish_book(
        file_path=pdf_path,
        name=product_name,
        price_cents=price_cents,
        description_html=f"<p>كتاب تلوين رقمي للأطفال — موضوع: {theme} ({pages_count} صفحة + غلاف)</p>",
        native_type="digital",
    )

    if publish_result["success"]:
        print(f"✅ تم النشر بنجاح! رابط الشراء: {publish_result['buy_link']}")
        add_product(product_name, publish_result["buy_link"], price_cents, "coloring_book", description=theme)
        log_operation("coloring_book", "success", message=publish_result["buy_link"], product_name=product_name)
    else:
        log_operation("coloring_book", "failed", message=publish_result["error"], product_name=product_name)
        raise SystemExit(f"❌ فشل النشر: {publish_result['error']}")


if __name__ == "__main__":
    main()
