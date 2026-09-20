"""
news_spider.py — التدوينات والأخبار العالمية (بمصادر حقيقية)
------------------------------------------------------------------
كيجيب أخبار حقيقية من الإنترنت عبر NewsAPI.org (ماشي توليد من عند LLM
لوحدو)، ومن بعد كيكتب تدوينة/مقال يلخص ويحلل هاد الأخبار بأسلوبه
الخاص، مع نسب كل معلومة لمصدرها (اسم + رابط) بدل ما ينسخها حرفياً.

⚠️ NewsAPI (النسخة المجانية): 100 طلب/اليوم، شهر وحد من الأرشيف فقط،
ومخصصة رسمياً "لتطوير Development" — إيلا بغيتي الاستعمال الإنتاجي
الكامل (نشر تلقائي يومي)، خاصك تترقى لخطة مدفوعة عند NewsAPI.

الإعداد: خاصك NEWSAPI_KEY (مجاني من newsapi.org).
"""

import os
import requests
from groq import Groq, APIError, APIConnectionError, RateLimitError

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
MODEL = "llama-3.1-8b-instant"


def fetch_news(query: str, language: str = "en", page_size: int = 5) -> dict:
    """
    كيرجع dict: {"success": bool, "articles": list[dict], "error": str|None}
    كل article فيه: title, source, url, description
    """
    if not NEWSAPI_KEY:
        return {"success": False, "articles": [], "error": "NEWSAPI_KEY ناقص."}

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": language,
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "apiKey": NEWSAPI_KEY,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return {"success": False, "articles": [], "error": data.get("message", "خطأ من NewsAPI.")}

        articles = [
            {
                "title": a.get("title", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", ""),
                "description": a.get("description", "") or "",
            }
            for a in data.get("articles", [])
        ]
        return {"success": True, "articles": articles, "error": None}

    except requests.exceptions.RequestException as e:
        return {"success": False, "articles": [], "error": str(e)}


def write_blog_post(client: Groq, topic: str, articles: list, language: str) -> str:
    """
    كيكتب تدوينة بناءً على الأخبار الحقيقية اللي جابها fetch_news، مع نسب
    كل معلومة لمصدرها. النموذج ممنوع يختلق معلومات ماكانتش فالمصادر.
    """
    if not articles:
        return "⚠️ ماكاينش أخبار باش نكتبو عليها — جرب موضوع آخر."

    sources_block = "\n".join(
        f"- [{a['source']}] {a['title']} — {a['description']} (رابط: {a['url']})"
        for a in articles
    )

    system_prompt = f"""You are a professional journalist and blogger writing in {language}.
Write a well-structured blog post about "{topic}" based STRICTLY on the source articles \
provided below. Rules:
- Do NOT invent facts, quotes, or details not present in the sources.
- Paraphrase in your own words — do not copy sentences verbatim from the sources.
- Every factual claim must be attributed to its source by name, e.g. "According to [Source Name]...".
- At the end, add a "المصادر / Sources" section listing each source name with its URL.
- Structure: a short intro, 2-4 body sections with clear headers, and a brief conclusion.
"""
    user_prompt = f"Sources:\n{sources_block}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip()
    except (RateLimitError, APIConnectionError, APIError) as e:
        return f"⚠️ خطأ من Groq API: {e}"
    except Exception as e:
        return f"⚠️ خطأ غير متوقع: {e}"


def generate_news_post(client: Groq, topic: str, language: str = "العربية") -> dict:
    """
    الدالة الشاملة: يجيب الأخبار ويكتب التدوينة فخطوة وحدة.
    يرجع dict: {"success": bool, "post": str|None, "sources_count": int, "error": str|None}
    """
    news = fetch_news(topic, language="en")  # NewsAPI كيخدم أحسن بالإنجليزية للبحث الواسع
    if not news["success"]:
        return {"success": False, "post": None, "sources_count": 0, "error": news["error"]}

    post = write_blog_post(client, topic, news["articles"], language)
    return {"success": True, "post": post, "sources_count": len(news["articles"]), "error": None}
