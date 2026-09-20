"""
compile_pdf.py — تجميع الصور فـ PDF واحد (لكتب التلوين، الملصقات، إلخ)
--------------------------------------------------------------------------
كياخذ لائحة صور (غلاف + صفحات) وكيبنيهم صفحة PDF كاملة لكل صورة، بالحجم
المناسب للطباعة (A4)، جاهز للرفع مباشرة على Gumroad.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _draw_image_full_page(c: canvas.Canvas, image_path: str, page_width: float, page_height: float) -> None:
    img = ImageReader(image_path)
    img_width, img_height = img.getSize()

    # نحسبو الحجم باش الصورة تدخل كاملة فالصفحة بلا ما تتقطع (مع هامش بسيط)
    margin = 20
    max_width = page_width - 2 * margin
    max_height = page_height - 2 * margin
    scale = min(max_width / img_width, max_height / img_height)
    draw_width = img_width * scale
    draw_height = img_height * scale

    x = (page_width - draw_width) / 2
    y = (page_height - draw_height) / 2
    c.drawImage(img, x, y, width=draw_width, height=draw_height)


def compile_images_to_pdf(image_paths: list, output_pdf_path: str) -> dict:
    """
    كل صورة فـ image_paths كتولي صفحة PDF كاملة (بالترتيب اللي عطيتيه).
    يرجع dict: {"success": bool, "path": str|None, "error": str|None}
    """
    if not image_paths:
        return {"success": False, "path": None, "error": "ماكاينش صور باش نجمعو."}

    try:
        page_width, page_height = A4
        c = canvas.Canvas(output_pdf_path, pagesize=A4)

        for image_path in image_paths:
            _draw_image_full_page(c, image_path, page_width, page_height)
            c.showPage()

        c.save()
        return {"success": True, "path": output_pdf_path, "error": None}

    except Exception as e:
        return {"success": False, "path": None, "error": str(e)}
