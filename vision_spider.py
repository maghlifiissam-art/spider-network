"""
vision_spider.py — من الصورة للوصف الهندسي
------------------------------------------------------------------
كياخذ صورة (منتج حقيقي، رسم، أو حتى تصور خيالي) ويحولها لوصف نصي غني
مفصل، جاهز يتحقن مباشرة فـ engineering_spider.design_part() كأنه وصف
كتبو المستخدم بنفسو.

⚠️ نقطة صدق مهمة يجب فهمها: بلا مرجع حقيقي فالصورة (خط قياس، جسم معروف
الحجم)، الموديل ما يقدرش "يشوف" الأبعاد الحقيقية بالميليمتر — غير يقدر
يقترحها بناءً على تناسب الشكل مع أشياء مشابهة. لهذا:
  - إيلا عطيتي known_reference_mm (مثلاً "الثقب اللي بان قطرو معروف = 8mm")
    الموديل غادي يستعملو كمرجع لتقدير باقي الأبعاد بدقة أحسن
  - بلا مرجع، الوصف كيرجع بمستوى ثقة "low" ويصرح بهذا فالنتيجة

يستعمل: meta-llama/llama-4-scout-17b-16e-instruct (نموذج Groq اللي كيشوف الصور)
"""

import base64
import json
from groq import Groq

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{data}"


def describe_product_from_image(client: Groq, image_path: str, known_reference_mm: str = "") -> dict:
    """
    يرجع dict:
      {"description": "...", "confidence": "low"|"medium", "detected_object": "...", "error": None}
    "description" مكتوب بشكل يقدر ينحقن مباشرة فـ engineering_spider.design_part()
    """
    image_data_uri = _encode_image(image_path)

    reference_note = (
        f'The user provided this known reference measurement to calibrate scale: "{known_reference_mm}". '
        "Use it to estimate other dimensions proportionally."
        if known_reference_mm
        else "No reference measurement was given — estimate dimensions based on typical real-world "
        "proportions for this type of object, and clearly mark confidence as low."
    )

    system_prompt = f"""You are a mechanical engineer's assistant. Look at the image and describe \
the object as a manufacturable mechanical part brief, suitable for a CAD design pipeline.

{reference_note}

Respond ONLY with valid JSON, no markdown fences:
{{
  "detected_object": "short name of what you see",
  "description": "a rich paragraph describing the part's shape, approximate dimensions in mm, \
likely material, and function — written as if a person were describing it for a part design request",
  "confidence": "low" or "medium",
  "notes": "any caveats about what's uncertain from the image"
}}"""

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ],
                }
            ],
            temperature=0.3,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        result["error"] = None
        return result
    except json.JSONDecodeError:
        return {"error": "فشل النموذج فإرجاع وصف صالح (JSON).", "description": None}
    except Exception as e:
        return {"error": str(e), "description": None}
