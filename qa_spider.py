"""
qa_spider.py — وكيل مراقبة الجودة ومكافحة الهلوسة
------------------------------------------------------------------
⚠️ حدود مهمة يجب معرفتها: هذا وكيل يعتمد على نفس نوع النموذج (LLM)
اللي كتب المحتوى الأصلي — فهو يقدر يكتشف مشاكل واضحة (تناقضات، ادعاءات
مبالغ فيها، أرقام بلا مصدر، وعود غير واقعية)، لكن ما يقدرش "يتأكد" من
صحة معلومة بشكل قاطع بحال ما يديرها إنسان أو بحث حقيقي على الإنترنت.
استعملو كخط دفاع إضافي (فلتر أول) ماشي كضمان مطلق.

الوظيفة الأساسية: review_content() — كتاخذ أي نص (تدوينة، إعلان،
وصف منتج...) وترجع تقرير مراجعة منظم.
"""

import json
from groq import Groq, APIError, APIConnectionError, RateLimitError

MODEL = "llama-3.1-8b-instant"


def review_content(client: Groq, content: str, context: str = "", language: str = "العربية") -> dict:
    """
    context: معلومات إضافية تساعد المراجعة (مثلاً: "هذا محتوى تسويقي لمنتج X، الثمن الحقيقي 199 درهم")
    يرجع dict: {"verdict": "ok"|"needs_review", "issues": [...], "summary": "..."}
    ولا {"error": "..."} إيلا طاح شي حاجة.
    """
    system_prompt = f"""You are a strict quality-control and fact-consistency reviewer for AI-generated \
marketing/content copy. You do NOT have internet access, so you cannot verify external facts — your job \
is to catch INTERNAL problems:
- Contradictions within the text itself
- Suspiciously specific numbers/statistics/dates presented with no source
- Overpromising or unrealistic claims (e.g. "guaranteed to make $10,000/month")
- Claims that contradict the provided context (if any)
- Missing disclaimers where clearly needed (e.g. financial/health claims)
- Tone or factual inconsistency between different parts of the text

Respond ONLY with a valid JSON object, no markdown fences:
{{
  "verdict": "ok" or "needs_review",
  "issues": ["short description of issue 1", "..."],
  "summary": "one-sentence overall assessment, written in {language}"
}}
If you find nothing wrong, return an empty issues list and verdict "ok"."""

    user_prompt = f"Context (may be empty): {context}\n\nContent to review:\n{content}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except (RateLimitError, APIConnectionError, APIError) as e:
        return {"error": f"خطأ من Groq API: {e}"}
    except json.JSONDecodeError:
        return {"error": "فشل تحليل استجابة المراجعة (JSON)."}
    except Exception as e:
        return {"error": f"خطأ غير متوقع: {e}"}
