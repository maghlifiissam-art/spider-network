"""
app.py — Spider Network Operations
-----------------------------------
نظام متعدد الوكلاء (Multi-Agent System) مبني بـ Streamlit + Groq API.

3 وكلاء متخصصون (Spiders):
  1. Affiliate Spider  — محلل سوق واستراتيجي أفلييت
  2. Media Spider       — صانع محتوى فيروسي وHooks نفسية
  3. Digital Products Spider — مهندس منتجات رقمية وSEO

كل وكيل عندو System Prompt خاص بيه، ومخرجات منظمة بصيغة Markdown،
مع دعم كامل للعربية/الفرنسية/الإنجليزية.
"""

import streamlit as st
from groq import Groq, APIError, APIConnectionError, RateLimitError

# ---------------------------------------------------------------------------
# إعدادات عامة
# ---------------------------------------------------------------------------
MODEL = "llama-3.1-8b-instant"

st.set_page_config(
    page_title="Spider Network Operations",
    page_icon="🕷️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# تعريف الوكلاء الثلاثة: System Prompts + Personas
# ---------------------------------------------------------------------------
AGENTS = {
    "affiliate": {
        "label": "🕸️ Affiliate Spider — عنكبوت الأفلييت واقتناص الترندات",
        "system_prompt": """You are the Affiliate Spider, an autonomous market analyst \
and affiliate strategist specialized in North African and global digital markets.

Your job: identify high-potential micro-niches, traffic-hijacking blueprints, the best \
platform selection (local/global), high-converting email swipe copies, and localized \
promotional frameworks.

Focus heavily on high-intent buyer psychology, organic search positioning, and \
actionable, concrete execution steps — never vague theory.

Always structure your output in clean Markdown with clear headers:
## الفرصة (Opportunity)
## الجمهور المستهدف (Target Audience)
## خطة الاستحواذ على الترافيك (Traffic Plan)
## نص إيميل جاهز (Swipe Copy)
## الخطوة التالية (Next Action)
""",
    },
    "media": {
        "label": "🎬 Media Spider — عنكبوت صناعة الإعلانات والـ Hooks النفسية",
        "system_prompt": """You are the Media Spider, a viral growth hacker and \
direct-response copywriter.

Your job: generate psychological ad hooks, short-form video scripts (Reels/TikTok), \
messaging funnel structures, and high-converting ad copy that triggers immediate \
buying intent.

Emphasize emotional triggers, pattern interrupts, and sharp, compelling phrasing \
designed to stop the scroll and drive action.

Always structure your output in clean Markdown with clear headers:
## الهوك الافتتاحي (Opening Hook)
## سكريبت الفيديو / Storyboard (3 مشاهد)
## نص الإعلان (Ad Copy)
## Call To Action
""",
    },
    "digital": {
        "label": "📚 Digital Products Spider — عنكبوت المنتجات الرقمية وهندسة المحتوى",
        "system_prompt": """You are the Digital Products Spider, a digital product \
architect and SEO content strategist.

Your job: design complete blueprints for e-books, micro-courses, pricing \
architectures, automated sales funnel steps, and SEO-optimized blogging strategies.

Structure the output into clear modules, chapter titles, audience pain points, and \
step-by-step launch frameworks.

Always structure your output in clean Markdown with clear headers:
## فكرة المنتج (Product Idea)
## المخطط / الفصول (Outline / Modules)
## التسعير المقترح (Pricing)
## خطة الإطلاق (Launch Funnel)
## كلمات مفتاحية SEO
""",
    },
}

LANGUAGES = {
    "العربية": "Respond entirely in Arabic (Modern Standard Arabic, clear and professional).",
    "Français": "Respond entirely in French.",
    "English": "Respond entirely in English.",
}

LANES = {
    "Fast Lane ⚡ (سريع)": {
        "desc": "نتيجة سريعة ومختصرة — فكرة واحدة قوية وقابلة للتنفيذ فوراً.",
        "max_tokens": 500,
        "extra_instruction": "Keep the answer concise and under 200 words total.",
    },
    "Guarded Lane 🛡️ (متعمق)": {
        "desc": "تحليل أعمق وأشمل — عدة خيارات مدروسة مع تفاصيل تنفيذية.",
        "max_tokens": 1200,
        "extra_instruction": "Provide a thorough, detailed answer with multiple options where relevant.",
    },
}

# ---------------------------------------------------------------------------
# دالة استدعاء Groq API مع معالجة أخطاء قوية
# ---------------------------------------------------------------------------
def call_spider(client: Groq, agent_key: str, user_topic: str, language: str, lane: str) -> str:
    agent = AGENTS[agent_key]
    lane_cfg = LANES[lane]

    system_prompt = (
        agent["system_prompt"]
        + f"\n\n{LANGUAGES[language]}\n{lane_cfg['extra_instruction']}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic / Niche: {user_topic}"},
            ],
            temperature=0.75,
            max_tokens=lane_cfg["max_tokens"],
        )
        return response.choices[0].message.content.strip()

    except RateLimitError:
        return "⚠️ تم تجاوز الحد المسموح من الطلبات (Rate Limit). حاول من بعد شوية دقائق."
    except APIConnectionError:
        return "⚠️ مشكل فالاتصال بـ Groq API. تأكد من الإنترنت وعاود المحاولة."
    except APIError as e:
        return f"⚠️ خطأ من طرف Groq API: {e}"
    except Exception as e:  # فيلتر أخير باش التطبيق ما يطيحش أبداً
        return f"⚠️ خطأ غير متوقع: {e}"


# ---------------------------------------------------------------------------
# الواجهة (UI)
# ---------------------------------------------------------------------------
def main():
    st.title("🕷️ Spider Network Operations")
    st.caption("نظام متعدد الوكلاء — Affiliate / Media / Digital Products")

    # --- الشريط الجانبي: مفتاح API وإعدادات عامة ---
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=st.secrets.get("GROQ_API_KEY", ""),
            help="يمكن تخزينه بشكل دائم في st.secrets بدل كتابته هنا كل مرة.",
        )
        language = st.selectbox("لغة المخرجات", list(LANGUAGES.keys()))
        lane = st.radio("وضع التوليد", list(LANES.keys()))
        st.caption(LANES[lane]["desc"])

        st.divider()
        if "history" not in st.session_state:
            st.session_state.history = []
        st.metric("عدد النتائج فهاد الجلسة", len(st.session_state.history))
        if st.session_state.history and st.button("🗑️ مسح السجل"):
            st.session_state.history = []
            st.rerun()

    if not api_key:
        st.warning("دخل Groq API Key من الشريط الجانبي باش تبدا.")
        st.stop()

    client = Groq(api_key=api_key)

    # --- تبويبات الوكلاء الثلاثة ---
    tabs = st.tabs([AGENTS[k]["label"] for k in AGENTS])

    for tab, agent_key in zip(tabs, AGENTS.keys()):
        with tab:
            st.subheader(AGENTS[agent_key]["label"])
            topic = st.text_area(
                "الموضوع / النيتش / المنتج",
                key=f"input_{agent_key}",
                placeholder="مثال: منتجات العناية بالبشرة الطبيعية فالسوق المغربي...",
                height=100,
            )
            col1, col2 = st.columns([1, 4])
            with col1:
                run = st.button("🚀 شغّل الوكيل", key=f"run_{agent_key}", use_container_width=True)

            if run:
                if not topic.strip():
                    st.error("خاصك تكتب موضوع/نيتش قبل ما تشغل الوكيل.")
                else:
                    with st.spinner("الوكيل خدام..."):
                        result = call_spider(client, agent_key, topic, language, lane)

                    st.markdown(result)

                    st.session_state.history.append(
                        {
                            "agent": AGENTS[agent_key]["label"],
                            "topic": topic,
                            "result": result,
                        }
                    )

                    st.download_button(
                        "⬇️ تحميل النتيجة",
                        data=result,
                        file_name=f"{agent_key}_result.md",
                        mime="text/markdown",
                        key=f"dl_{agent_key}",
                    )

    # --- سجل النتائج ---
    if st.session_state.history:
        st.divider()
        with st.expander(f"📜 سجل النتائج ({len(st.session_state.history)})"):
            for i, entry in enumerate(reversed(st.session_state.history), 1):
                st.markdown(f"**{i}. {entry['agent']}** — _{entry['topic']}_")
                st.markdown(entry["result"])
                st.markdown("---")


if __name__ == "__main__":
    main()
