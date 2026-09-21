"""
pages/4_📚_Book_Spider.py
---------------------------
واجهة Streamlit لوكيل الكتب الرقمية والقصص المصورة (Book Spider).

باش تخدم: حط هاد الملف داخل مجلد `pages/` جنب `app.py` ديالك — Streamlit
كيتعرف تلقائياً على أي ملف فمجلد pages/ ويزيدو كصفحة/تبويب إضافي فالتطبيق.
"""

import os

import streamlit as st

def _groq_key_from_secrets() -> str:
    """Read GROQ_API_KEY from st.secrets when configured, else the environment."""
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return os.environ.get("GROQ_API_KEY", "")

from groq import Groq

from book_spider import (
    generate_full_book,
    generate_illustrated_story,
    regenerate_variant,
    VARIANT_TYPES,
)

st.set_page_config(page_title="Book Spider", page_icon="📚", layout="wide")
from rtl_support import inject_rtl
inject_rtl()
st.title("📚 Book Spider — الكتب الرقمية والقصص المصورة")
st.caption("توليد كتب رقمية عند الطلب، قصص مصورة (سيناريو نصي)، وتنويعات لكتب جاهزة. (نص فقط دابا — الصور تتزاد من بعد)")

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("Groq API Key", type="password", value=_groq_key_from_secrets())
    language = st.selectbox("اللغة", ["العربية", "Français", "English"])

if not api_key:
    st.warning("دخل Groq API Key باش تبدا.")
    st.stop()

client = Groq(api_key=api_key)

mode = st.radio(
    "شنو بغيتي تدير؟",
    ["📖 كتاب جديد كامل", "🖼️ قصة مصورة (سيناريو)", "🔁 تنويع كتاب جاهز"],
    horizontal=True,
)

# ---------------------------------------------------------------------------
# وضع 1: كتاب جديد كامل — يتبنى فصل بفصل مع عرض التقدم
# ---------------------------------------------------------------------------
if mode == "📖 كتاب جديد كامل":
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("موضوع الكتاب", placeholder="مثال: دليل بدء التجارة الإلكترونية فالمغرب")
        genre = st.selectbox("النوع", ["دليل عملي / How-to", "قصة/رواية قصيرة", "كتاب تعليمي", "مذكرات/تجربة شخصية"])
    with col2:
        chapters_count = st.slider("عدد الفصول", 3, 12, 5)

    if st.button("🚀 ابدأ توليد الكتاب", use_container_width=True):
        if not topic.strip():
            st.error("خاصك تكتب موضوع الكتاب.")
        else:
            progress = st.progress(0, text="كنبنيو المخطط...")
            book_container = st.container()
            full_book_text = ""
            chapter_done = 0

            for event_type, payload in generate_full_book(client, topic, genre, language, chapters_count):
                if event_type == "outline":
                    st.session_state["current_outline"] = payload
                    with book_container:
                        st.subheader(payload.get("title", topic))
                        if payload.get("subtitle"):
                            st.caption(payload["subtitle"])
                elif event_type == "chapter":
                    chapter_done += 1
                    progress.progress(
                        chapter_done / chapters_count,
                        text=f"كتبنا الفصل {chapter_done}/{chapters_count}...",
                    )
                    with book_container:
                        st.markdown(f"### {payload['chapter'].get('number')}. {payload['chapter'].get('title')}")
                        st.markdown(payload["content"])
                elif event_type == "done":
                    full_book_text = payload
                    progress.progress(1.0, text="✅ الكتاب كمل!")

            if full_book_text:
                st.session_state["last_book_text"] = full_book_text
                st.session_state["last_book_title"] = st.session_state.get("current_outline", {}).get("title", topic)
                st.download_button(
                    "⬇️ تحميل الكتاب كامل (Markdown)",
                    data=full_book_text,
                    file_name="book.md",
                    mime="text/markdown",
                )

# ---------------------------------------------------------------------------
# وضع 2: قصة مصورة (سيناريو نصي لوحة بلوحة)
# ---------------------------------------------------------------------------
elif mode == "🖼️ قصة مصورة (سيناريو)":
    topic = st.text_input("موضوع/فكرة القصة", placeholder="مثال: عنكبوت صغير كيكتشف المدينة لأول مرة")
    panels_count = st.slider("عدد اللوحات", 4, 16, 8)

    if st.button("🚀 ولّد السيناريو", use_container_width=True):
        if not topic.strip():
            st.error("خاصك تكتب فكرة القصة.")
        else:
            with st.spinner("كنكتبو السيناريو..."):
                story = generate_illustrated_story(client, topic, language, panels_count)
            st.markdown(story)
            st.download_button("⬇️ تحميل السيناريو", data=story, file_name="story_script.md", mime="text/markdown")
            st.info("💡 كل لوحة فيها `image_prompt` جاهز — غادي يتستعمل مباشرة ملي نزيدو API ديال الصور.")

# ---------------------------------------------------------------------------
# وضع 3: تنويع كتاب جاهز (غلاف / أسلوب / أمثلة)
# ---------------------------------------------------------------------------
elif mode == "🔁 تنويع كتاب جاهز":
    if "last_book_text" not in st.session_state:
        st.warning("خاصك تولد كتاب من وضع '📖 كتاب جديد كامل' أولاً، ولا تلصق محتوى كتاب موجود هنا تحت.")
        reference_content = st.text_area("الصق محتوى الكتاب المرجعي هنا (اختياري)", height=200)
        book_title = st.text_input("عنوان الكتاب", value="")
    else:
        reference_content = st.session_state["last_book_text"]
        book_title = st.session_state.get("last_book_title", "")
        st.success(f"غادي نخدمو على آخر كتاب مولّد: **{book_title}**")

    tone = st.text_input("النبرة/الأسلوب الحالي", value="احترافي")
    variant_label = st.selectbox(
        "شنو بغيتي تنوع؟",
        list(VARIANT_TYPES.keys()),
        format_func=lambda k: {
            "cover_concept": "🎨 مفهوم غلاف جديد",
            "tone": "🗣️ أسلوب/نبرة مختلفة",
            "examples": "📌 أمثلة جديدة",
        }[k],
    )

    if st.button("🔁 ولّد التنويع", use_container_width=True):
        if not reference_content.strip():
            st.error("خاصنا محتوى مرجعي (كتاب مولّد قبل، ولا نص تلصقو).")
        else:
            with st.spinner("كنولدو التنويع..."):
                variant = regenerate_variant(client, book_title, tone, language, variant_label, reference_content)
            st.markdown(variant)
            st.download_button("⬇️ تحميل التنويع", data=variant, file_name=f"variant_{variant_label}.md", mime="text/markdown")
