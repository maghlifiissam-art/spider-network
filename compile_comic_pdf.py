"""
compile_comic_pdf.py — بناء القصة المصورة الكاملة (صور + حوار) كـ PDF
----------------------------------------------------------------------
1. generate_panel_images() -> كيولد صورة لكل لوحة عبر Pollinations.ai
2. compile_comic_to_pdf()  -> كيبني PDF: كل لوحة = صورة + الحوار مكتوب
   تحتها. دعم خاص للعربية (تشكيل الحروف + اتجاه RTL) عبر arabic_reshaper
   و python-bidi، مع تحميل خط Noto Naskh Arabic أوتوماتيكياً أول مرة.
"""

import os
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from visual_spider import _fetch_image  # نعاود نستعملو نفس دالة التحميل من Pollinations

ARABIC_FONT_NAME = "NotoNaskhArabic"
ARABIC_FONT_PATH = "fonts/NotoNaskhArabic-Regular.ttf"
ARABIC_FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/"
    "notonaskharabic/NotoNaskhArabic-Regular.ttf"
)


def _ensure_arabic_font() -> str:
    """كيحمل خط عربي مرة وحدة إيلا ماكانش موجود محلياً، ويرجع المسار."""
    if not os.path.exists(ARABIC_FONT_PATH):
        os.makedirs(os.path.dirname(ARABIC_FONT_PATH), exist_ok=True)
        resp = requests.get(ARABIC_FONT_URL, timeout=30)
        resp.raise_for_status()
        with open(ARABIC_FONT_PATH, "wb") as f:
            f.write(resp.content)
    return ARABIC_FONT_PATH


def _shape_arabic(text: str) -> str:
    """كيرجع النص العربي مشكّل ومرتب بالاتجاه الصحيح (RTL) للعرض فـ PDF."""
    import arabic_reshaper
    from bidi.algorithm import get_display

    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# ---------------------------------------------------------------------------
# 1) توليد صورة لكل لوحة
# ---------------------------------------------------------------------------
def generate_panel_images(panels: list, output_dir: str) -> dict:
    """
    panels: لائحة dicts فيها على الأقل "number" و "image_prompt" (من comic_spider).
    يرجع dict: {"success": bool, "image_paths": {panel_number: path}, "errors": list}
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = {}
    errors = []

    for panel in panels:
        number = panel["number"]
        result = _fetch_image(panel["image_prompt"], width=1024, height=1024, seed=number)
        if result["success"]:
            path = os.path.join(output_dir, f"panel_{number:02d}.jpg")
            with open(path, "wb") as f:
                f.write(result["bytes"])
            image_paths[number] = path
        else:
            errors.append(f"لوحة {number}: {result['error']}")

    return {"success": len(image_paths) > 0, "image_paths": image_paths, "errors": errors}


# ---------------------------------------------------------------------------
# 2) تجميع الصور + الحوار فـ PDF
# ---------------------------------------------------------------------------
def compile_comic_to_pdf(panels: list, image_paths: dict, output_pdf_path: str, language: str) -> dict:
    try:
        page_width, page_height = A4
        c = canvas.Canvas(output_pdf_path, pagesize=A4)

        is_arabic = language.strip() in ("العربية", "Arabic", "ar")
        if is_arabic:
            font_path = _ensure_arabic_font()
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, font_path))
            font_name = ARABIC_FONT_NAME
        else:
            font_name = "Helvetica"

        margin = 30
        caption_height = 90
        image_area_height = page_height - 2 * margin - caption_height

        for panel in panels:
            number = panel["number"]
            path = image_paths.get(number)
            if not path:
                continue  # لوحة فشل توليدها — نتخطاوها بدل ما نوقفو الكتاب كامل

            img = ImageReader(path)
            img_w, img_h = img.getSize()
            max_w = page_width - 2 * margin
            scale = min(max_w / img_w, image_area_height / img_h)
            draw_w, draw_h = img_w * scale, img_h * scale
            x = (page_width - draw_w) / 2
            y = page_height - margin - draw_h
            c.drawImage(img, x, y, width=draw_w, height=draw_h)

            # --- الحوار/التعليق تحت الصورة ---
            dialogue = panel.get("dialogue", "")
            c.setFont(font_name, 13)
            text_y = y - 25
            display_text = _shape_arabic(dialogue) if is_arabic else dialogue

            if is_arabic:
                c.drawRightString(page_width - margin, text_y, display_text)
            else:
                c.drawString(margin, text_y, display_text)

            c.showPage()

        c.save()
        return {"success": True, "path": output_pdf_path, "error": None}

    except Exception as e:
        return {"success": False, "path": None, "error": str(e)}
