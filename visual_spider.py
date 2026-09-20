"""
visual_spider.py — الملصقات، الشعارات، وكتب التلوين للأطفال
------------------------------------------------------------------
كيستعمل Pollinations.ai (endpoint القديم: image.pollinations.ai) — مجاني
بالكامل وبلا API key.

⚠️ حدود النسخة المجانية (anonymous tier):
   - طلب واحد كل 15 ثانية تقريباً (rate limit)
   - يمكن يزيد علامة مائية خفيفة (watermark)
   -> إيلا بغيتي تفادي هاد الحدود: سجل مجاناً فـ auth.pollinations.ai
      وحط التوكن فـ POLLINATIONS_TOKEN (اختياري، الكود كيخدم بلاه).

الوظائف:
  1. generate_poster()       -> ملصق/بوستر (تسويقي، إعلاني، مناسبات)
  2. generate_logo()         -> شعار بسيط، فلات، خلفية بيضاء
  3. generate_coloring_page() -> صفحة تلوين واحدة للأطفال (خطوط سوداء فقط)
  4. generate_coloring_book() -> كتاب تلوين كامل (غلاف + عدة صفحات بنفس الثيم)
"""

import os
import time
import requests
from urllib.parse import quote

BASE_URL = "https://image.pollinations.ai/prompt"
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN", "")
ANONYMOUS_DELAY_SECONDS = 15  # احترام حد الطلب الواحد كل 15 ثانية للمجهولين


def _fetch_image(prompt: str, width: int = 1024, height: int = 1024, seed: int | None = None) -> dict:
    """
    كينزل الصورة ويرجع dict: {"success": bool, "bytes": bytes|None, "error": str|None}
    """
    url = f"{BASE_URL}/{quote(prompt)}"
    params = {"width": width, "height": height, "nologo": "true"}
    if seed is not None:
        params["seed"] = seed
    if POLLINATIONS_TOKEN:
        params["token"] = POLLINATIONS_TOKEN

    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return {"success": True, "bytes": resp.content, "error": None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "bytes": None, "error": str(e)}
    finally:
        if not POLLINATIONS_TOKEN:
            time.sleep(ANONYMOUS_DELAY_SECONDS)  # احترام الحد إيلا ماكانش توكن


def _save(image_bytes: bytes, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image_bytes)


# ---------------------------------------------------------------------------
# 1) ملصق / بوستر
# ---------------------------------------------------------------------------
def generate_poster(topic: str, style: str, output_path: str) -> dict:
    prompt = (
        f"professional marketing poster about {topic}, style: {style}, "
        "bold typography space, high contrast, eye-catching composition, "
        "advertising design, clean layout, 4k"
    )
    result = _fetch_image(prompt, width=1080, height=1350)
    if result["success"]:
        _save(result["bytes"], output_path)
        result["path"] = output_path
    return result


# ---------------------------------------------------------------------------
# 2) شعار (Logo)
# ---------------------------------------------------------------------------
def generate_logo(brand_name: str, style_keywords: str, output_path: str) -> dict:
    prompt = (
        f"minimalist flat vector logo for a brand called '{brand_name}', "
        f"{style_keywords}, simple geometric shapes, white background, "
        "no text artifacts, professional branding, vector art style"
    )
    result = _fetch_image(prompt, width=1024, height=1024)
    if result["success"]:
        _save(result["bytes"], output_path)
        result["path"] = output_path
    return result


# ---------------------------------------------------------------------------
# 3) صفحة تلوين واحدة للأطفال
# ---------------------------------------------------------------------------
def generate_coloring_page(subject: str, output_path: str, seed: int | None = None) -> dict:
    prompt = (
        f"black and white coloring book page for kids, {subject}, "
        "thick clean outlines only, no shading, no color, no grayscale, "
        "simple friendly cartoon style, white background, "
        "safe and cheerful for young children"
    )
    result = _fetch_image(prompt, width=1024, height=1024, seed=seed)
    if result["success"]:
        _save(result["bytes"], output_path)
        result["path"] = output_path
    return result


# ---------------------------------------------------------------------------
# 4) كتاب تلوين كامل (غلاف + صفحات)
# ---------------------------------------------------------------------------
def generate_coloring_book(theme: str, pages_count: int, output_dir: str) -> dict:
    """
    كيبني كتاب تلوين كامل: غلاف ملون بسيط + N صفحة تلوين بنفس الثيم.
    يرجع dict: {"success": bool, "cover": str|None, "pages": list[str], "errors": list[str]}
    """
    os.makedirs(output_dir, exist_ok=True)
    errors = []

    # الغلاف: ألوان خفيفة (ماشي أبيض وأسود) باش يبان جذاب فالمعرض
    cover_prompt = (
        f"cute children's book cover illustration, theme: {theme}, "
        "colorful, warm and friendly, simple shapes, title space at top, "
        "digital illustration style for kids"
    )
    cover_result = _fetch_image(cover_prompt, width=1024, height=1365)
    cover_path = None
    if cover_result["success"]:
        cover_path = os.path.join(output_dir, "cover.jpg")
        _save(cover_result["bytes"], cover_path)
    else:
        errors.append(f"غلاف: {cover_result['error']}")

    pages = []
    for i in range(1, pages_count + 1):
        page_result = generate_coloring_page(
            subject=f"{theme}, scene {i}",
            output_path=os.path.join(output_dir, f"page_{i:02d}.jpg"),
            seed=i,  # seed مختلف لكل صفحة باش تكون متنوعة
        )
        if page_result["success"]:
            pages.append(page_result["path"])
        else:
            errors.append(f"صفحة {i}: {page_result['error']}")

    return {
        "success": len(pages) > 0,
        "cover": cover_path,
        "pages": pages,
        "errors": errors,
    }
