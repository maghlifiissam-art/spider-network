"""
agent_chain.py — الوكلاء المتسلسلون أوتوماتيكياً (Search → Write → Review)
------------------------------------------------------------------------------
كيربط 3 خطوات فمسلسل واحد:
  1. 🔍 بحث حقيقي (NewsAPI) — يجيب سياق/معطيات حديثة عن الموضوع
  2. ✍️ كتابة — أحد الوكلاء الثلاثة (Affiliate/Media/Digital) كيكتب المحتوى
     مستفيداً من نتائج البحث كسياق إضافي (ماشي كمصدر وحيد إجباري)
  3. 🔎 مراجعة — QA Spider كيراجع المسودة ويعلم أي مشكل قبل ما تنشر
"""

from groq import Groq
from news_spider import fetch_news
from qa_spider import review_content

MODEL = "llama-3.1-8b-instant"

WRITER_PROMPTS = {
    "affiliate": """You are the Affiliate Spider, an autonomous market analyst and affiliate \
strategist. Identify high-potential micro-niches, traffic acquisition angles, and actionable \
next steps. Use the research context provided (if relevant) to ground your suggestions in \
current trends, but do not fabricate statistics beyond what's given.""",
    "media": """You are the Media Spider, a viral growth hacker and direct-response copywriter. \
Generate psychological ad hooks and short-form video outlines. Use the research context (if \
relevant) to make hooks feel current and specific.""",
    "digital": """You are the Digital Products Spider, a digital product architect and SEO \
strategist. Propose digital product ideas, outlines, and launch plans. Use the research \
context (if relevant) to align with real current demand.""",
}


def run_chain(client: Groq, agent_type: str, topic: str, language: str = "العربية") -> dict:
    """
    يرجع dict: {
      "sources_used": int,
      "draft": str,
      "review": dict (من qa_spider),
      "final_note": str
    }
    """
    if agent_type not in WRITER_PROMPTS:
        return {"error": "agent_type غير معروف — خاصو يكون affiliate / media / digital."}

    # --- 1) البحث ---
    news = fetch_news(topic, language="en", page_size=5)
    research_context = ""
    sources_used = 0
    if news["success"] and news["articles"]:
        sources_used = len(news["articles"])
        research_context = "\n".join(
            f"- {a['title']} ({a['source']}): {a['description']}" for a in news["articles"]
        )
    # إيلا فشل البحث (مثلاً NEWSAPI_KEY ناقص)، الوكيل كيكمل بلا سياق بحث —
    # ماشي خطأ قاتل، غير جودة أقل دقة فالمعطيات الحديثة

    # --- 2) الكتابة ---
    system_prompt = (
        WRITER_PROMPTS[agent_type]
        + f"\nRespond entirely in {language}. Structure your output in clean Markdown."
    )
    user_prompt = f"Topic: {topic}\n\nRecent research context (may be empty):\n{research_context}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.75,
            max_tokens=900,
        )
        draft = response.choices[0].message.content.strip()
    except Exception as e:
        return {"error": f"فشلت خطوة الكتابة: {e}"}

    # --- 3) المراجعة ---
    review = review_content(
        client,
        content=draft,
        context=f"محتوى تسويقي من نوع {agent_type} حول: {topic}",
        language=language,
    )

    return {
        "sources_used": sources_used,
        "draft": draft,
        "review": review,
        "final_note": "✅ جاهز للنشر" if review.get("verdict") == "ok" else "⚠️ يحتاج مراجعة يدوية قبل النشر",
    }
