"""
comic_spider.py — سيناريو القصة المصورة (Bande Dessinée)
------------------------------------------------------------
كيبني سيناريو لوحة بلوحة بطريقتين:
  mode="prompt" -> تعطيه فكرة عامة (مثلاً "مغامرة فضائية") والوكيل كيبني
                   القصة كاملة (شخصيات، حبكة، لوحات) من الصفر.
  mode="script" -> تعطيه سيناريو/قصة كاملة كتبتيها نتا، والوكيل كيقسمها
                   للوحات (Panels) مع حوار وimage_prompt لكل وحدة.

مهم: الـ image_prompt ديال كل لوحة دايماً بالإنجليزية (أحسن نتائج مع
نماذج توليد الصور)، أما الحوار/التعليق فبيكتب باللغة اللي طلبتيها.
"""

import json
from groq import Groq, APIError, APIConnectionError, RateLimitError

MODEL = "llama-3.1-8b-instant"


def _safe_call(client: Groq, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except (RateLimitError, APIConnectionError, APIError) as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"خطأ غير متوقع: {e}"})


def generate_comic_script(client: Groq, language: str, panels_count: int, mode: str,
                           topic: str = "", user_script: str = "") -> dict:
    """
    يرجع dict: {"title": "...", "panels": [{"number", "scene", "dialogue", "image_prompt"}]}
    ولا {"error": "..."} إيلا طاح شي حاجة.
    """
    base_rules = f"""You are a professional comic book scriptwriter and storyboard artist.
Respond ONLY with a valid JSON object, no markdown fences, no extra text.
The JSON must have this exact shape:
{{
  "title": "...",
  "panels": [
    {{
      "number": 1,
      "scene": "short scene description in {language}",
      "dialogue": "dialogue or narration text in {language} (keep short, 1-2 lines)",
      "image_prompt": "a detailed visual description IN ENGLISH ONLY, comic book panel style, vibrant colors, dynamic composition, no text, no speech bubbles, no lettering"
    }}
  ]
}}
Produce exactly {panels_count} panels. The "dialogue" and "scene" fields must be written in {language}. \
The "image_prompt" field must ALWAYS be in English regardless of {language}."""

    if mode == "prompt":
        system_prompt = base_rules + "\nBuild a complete, coherent short story (characters, conflict, resolution) from the topic given by the user."
        user_prompt = f"Topic: {topic}"
    elif mode == "script":
        system_prompt = base_rules + "\nAdapt the user's own story/script into panels. Preserve their plot, characters and tone — do not invent a different story. Translate/adapt dialogue into the target language if needed."
        user_prompt = f"User's story/script:\n{user_script}"
    else:
        return {"error": "mode غير معروف — خاصو يكون 'prompt' ولا 'script'."}

    raw = _safe_call(client, system_prompt, user_prompt, max_tokens=2200)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": f"فشل تحليل استجابة النموذج (JSON). الخام: {raw[:300]}"}
