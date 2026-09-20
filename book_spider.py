"""
book_spider.py — Digital Books & Illustrated Stories Spider
-------------------------------------------------------------
وكيل توليد الكتب الرقمية والقصص المصورة (نص فقط دابا — الصور غادي تزاد
فمرحلة لاحقة عبر API خاص بالصور).

يشتغل بمبدأ "فصل بفصل" (chapter-by-chapter) باش يتفادى حدود الطول ديال
النموذج، ويقدر يبني كتاب كامل بجودة ثابتة.

الوظائف الأساسية:
  1. generate_outline()        -> يبني مخطط/فهرس الكتاب
  2. generate_chapter()        -> يكتب فصل واحد بناءً على المخطط
  3. generate_full_book()      -> يبني الكتاب كامل (مخطط + كل الفصول)
  4. generate_illustrated_story() -> سيناريو قصة مصورة (لوحة بلوحة)
  5. regenerate_variant()      -> يعيد توليد الغلاف/الأسلوب/الأمثلة لكتاب
                                   موجود بدون ما يبدل الهيكل العام
"""

import json
from groq import Groq, APIError, APIConnectionError, RateLimitError

MODEL = "llama-3.1-8b-instant"


def _safe_call(client: Groq, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
    """نداء موحد لـ Groq مع معالجة أخطاء قوية."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return "⚠️ تم تجاوز الحد المسموح (Rate Limit). حاول من بعد شوية."
    except APIConnectionError:
        return "⚠️ مشكل فالاتصال بـ Groq API."
    except APIError as e:
        return f"⚠️ خطأ من Groq API: {e}"
    except Exception as e:
        return f"⚠️ خطأ غير متوقع: {e}"


# ---------------------------------------------------------------------------
# 1) بناء مخطط الكتاب (فهرس + وصف كل فصل)
# ---------------------------------------------------------------------------
def generate_outline(client: Groq, topic: str, genre: str, language: str, chapters_count: int) -> dict:
    system_prompt = f"""You are a professional book architect and editor.
Respond ONLY with a valid JSON object, no markdown fences, no extra text.
The JSON must have this exact shape:
{{
  "title": "...",
  "subtitle": "...",
  "target_audience": "...",
  "tone": "...",
  "chapters": [
    {{"number": 1, "title": "...", "summary": "..."}}
  ]
}}
Write the content in {language}. Genre: {genre}. Produce exactly {chapters_count} chapters."""

    raw = _safe_call(client, system_prompt, f"Book topic: {topic}", max_tokens=1200)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # fallback: نرجعو هيكل بسيط باش التطبيق ما يطيحش
        return {
            "title": topic,
            "subtitle": "",
            "target_audience": "",
            "tone": genre,
            "chapters": [
                {"number": i + 1, "title": f"الفصل {i + 1}", "summary": ""}
                for i in range(chapters_count)
            ],
            "raw_fallback": raw,
        }


# ---------------------------------------------------------------------------
# 2) كتابة فصل واحد
# ---------------------------------------------------------------------------
def generate_chapter(client: Groq, book_title: str, tone: str, language: str,
                      chapter_title: str, chapter_summary: str, chapter_number: int) -> str:
    system_prompt = f"""You are a professional author writing chapter {chapter_number} of the \
book "{book_title}". Tone: {tone}. Write entirely in {language}.
Write a complete, well-structured chapter (roughly 400-600 words) in Markdown, with a \
short intro, developed body, and a closing takeaway. Do not repeat the chapter title as \
a heading — start directly with the content."""

    user_prompt = f"Chapter title: {chapter_title}\nChapter summary/brief: {chapter_summary}"
    return _safe_call(client, system_prompt, user_prompt, max_tokens=1000)


# ---------------------------------------------------------------------------
# 3) توليد الكتاب كامل (مخطط + كل الفصول) — مولّد (generator) باش نعرضو
#    التقدم فالواجهة فصل بفصل بدل ما نستناو الكتاب كامل
# ---------------------------------------------------------------------------
def generate_full_book(client: Groq, topic: str, genre: str, language: str, chapters_count: int):
    outline = generate_outline(client, topic, genre, language, chapters_count)
    yield ("outline", outline)

    full_text_parts = [f"# {outline.get('title', topic)}\n"]
    if outline.get("subtitle"):
        full_text_parts.append(f"*{outline['subtitle']}*\n")

    for chapter in outline.get("chapters", []):
        content = generate_chapter(
            client,
            book_title=outline.get("title", topic),
            tone=outline.get("tone", genre),
            language=language,
            chapter_title=chapter.get("title", ""),
            chapter_summary=chapter.get("summary", ""),
            chapter_number=chapter.get("number", 0),
        )
        chapter_md = f"\n## {chapter.get('number')}. {chapter.get('title')}\n\n{content}\n"
        full_text_parts.append(chapter_md)
        yield ("chapter", {"chapter": chapter, "content": content})

    yield ("done", "\n".join(full_text_parts))


# ---------------------------------------------------------------------------
# 4) قصة مصورة (Comic / Illustrated Story) — سيناريو لوحة بلوحة
#    كل لوحة فيها: وصف المشهد، الحوار، و image_prompt جاهز للاستعمال
#    مستقبلاً مع أي API صور (يتزاد فمرحلة لاحقة)
# ---------------------------------------------------------------------------
def generate_illustrated_story(client: Groq, topic: str, language: str, panels_count: int = 8) -> str:
    system_prompt = f"""You are a comic book writer and storyboard artist.
Write entirely in {language}. Create a short illustrated story with exactly \
{panels_count} panels.

For each panel, output in Markdown exactly this structure:
### لوحة N
**المشهد:** (scene description, visual details)
**الحوار:** (dialogue or narration, keep short)
**image_prompt:** (a detailed English prompt describing the visual, ready to feed to an \
image generation tool later)
"""
    return _safe_call(client, system_prompt, f"Story topic: {topic}", max_tokens=1800)


# ---------------------------------------------------------------------------
# 5) تنويع كتاب موجود: تبديل الغلاف/الأسلوب/الأمثلة بدون تبديل الهيكل
#    (مفيد لـ "كتب جاهزة" كتتباع بأشكال متعددة من نفس المحتوى الأساسي)
# ---------------------------------------------------------------------------
VARIANT_TYPES = {
    "cover_concept": "Generate ONLY a new book cover concept: title variant, subtitle variant, "
                      "and a detailed image_prompt (English) describing the cover artwork.",
    "tone": "Rewrite the SAME content outline but in a different tone/register (e.g. more "
            "formal, more casual, more humorous) — keep the same structure and facts.",
    "examples": "Keep the exact same structure, but regenerate all illustrative examples, "
                "case studies, and analogies used throughout with fresh ones.",
}


def regenerate_variant(client: Groq, book_title: str, tone: str, language: str,
                        variant_type: str, reference_content: str) -> str:
    if variant_type not in VARIANT_TYPES:
        return "⚠️ نوع التنويع غير معروف."

    system_prompt = f"""You are editing an existing book titled "{book_title}" (tone: {tone}). \
Write in {language}. {VARIANT_TYPES[variant_type]}
Base your output on the reference content given, but do not simply copy it."""

    return _safe_call(client, system_prompt, f"Reference content:\n{reference_content[:3000]}", max_tokens=900)
