"""
pages/7_⚙️_Engineering_Spider.py
-----------------------------------
عنكبوت الهندسة: من وصف نصي أو من صورة (منتج حقيقي أو خيالي) إلى قطعة
ميكانيكية بأبعاد حقيقية (STL) مع تحليل قوة التحمل. الشكل (دعامة/لوحة)
كيتحدد أوتوماتيكياً من الوصف.
"""

import os
import streamlit as st
from groq import Groq

from engineering_spider import design_part, MATERIALS
from vision_spider import describe_product_from_image

st.set_page_config(page_title="Engineering Spider", page_icon="⚙️", layout="wide")
st.title("⚙️ Engineering Spider")
st.warning("⚠️ هذا نموذج أولي للدراسة/التعلم فقط — أي تصميم هنا خاصو مراجعة مهندس مرخص قبل التصنيع أو الاستعمال الحقيقي.")

with st.sidebar:
    api_key = st.text_input("Groq API Key", type="password", value=st.secrets.get("GROQ_API_KEY", ""))
    st.markdown("**المواد المدعومة حالياً:**")
    for key, m in MATERIALS.items():
        st.caption(f"• {m['name_ar']} — إجهاد الخضوع: {m['yield_mpa']} MPa")
    st.markdown("**الأشكال المدعومة حالياً:** دعامة زاوية (L-Bracket)، لوحة بثقوب (Flat Plate)")

mode = st.radio("كيفاش بغيتي تدخل الفكرة؟", ["✍️ وصف نصي", "📷 صورة"], horizontal=True)

description = ""

if mode == "✍️ وصف نصي":
    description = st.text_area(
        "صف القطعة اللي بغيتي",
        placeholder="مثال: دعامة زاوية لتثبيت رف خشبي كيحمل تقريباً 15 كيلو، فالمطبخ",
        height=100,
    )
else:
    uploaded_image = st.file_uploader("زيد صورة المنتج (حقيقي أو حتى تصور خيالي)", type=["jpg", "jpeg", "png"])
    known_reference = st.text_input(
        "مرجع معروف فالصورة (اختياري، بزاف كيحسن الدقة)",
        placeholder="مثال: قطر الثقب فالصورة تقريباً 8mm",
    )
    if uploaded_image and api_key:
        temp_path = f"temp_upload_{uploaded_image.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_image.getbuffer())
        st.image(temp_path, caption="الصورة اللي زدتي", width=300)

        if st.button("🔍 حلل الصورة"):
            with st.spinner("كنحللو الصورة..."):
                client = Groq(api_key=api_key)
                vision_result = describe_product_from_image(client, temp_path, known_reference)

            if vision_result.get("error"):
                st.error(f"❌ {vision_result['error']}")
            else:
                st.session_state["vision_description"] = vision_result["description"]
                confidence_icon = "🟡" if vision_result["confidence"] == "low" else "🟢"
                st.info(f"{confidence_icon} مستوى الثقة: {vision_result['confidence']} — {vision_result.get('notes', '')}")
                st.write(f"**الوصف المستخرج:** {vision_result['description']}")

        os.remove(temp_path) if os.path.exists(temp_path) else None

    description = st.session_state.get("vision_description", "")
    if description:
        description = st.text_area("عدّل الوصف قبل التصميم إيلا حبيت", value=description, height=120)

if st.button("🚀 صمم القطعة", use_container_width=True):
    if not api_key:
        st.error("دخل Groq API Key.")
    elif not description.strip():
        st.error("خاصك تكتب وصف أو تحلل صورة أولاً.")
    else:
        with st.spinner("كنصممو..."):
            client = Groq(api_key=api_key)
            result = design_part(client, description)

        if not result["success"]:
            st.error(f"❌ {result.get('error', 'فشل غير معروف')}")
        else:
            spec = result["spec"]
            strength = result["strength_analysis"]

            st.success(f"الشكل المكتشف: {result['shape_type']}")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📐 المواصفات المقترحة")
                st.json(spec)
            with col2:
                st.subheader("🔧 تحليل قوة التحمل")
                st.metric("الإجهاد", f"{strength.get('bending_stress_mpa')} MPa")
                st.metric("معامل الأمان (FoS)", strength.get("factor_of_safety"))
                st.write(strength.get("verdict"))

            st.divider()
            with open(result["stl_path"], "rb") as f:
                st.download_button("⬇️ تحميل ملف STL", data=f, file_name="part.stl", mime="model/stl")

            st.info(result["disclaimer"])
