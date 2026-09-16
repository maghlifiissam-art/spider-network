import streamlit as st
import os
from groq import Groq

st.title("🕷️ غرفة عمليات شبكة العناكب")

# جلب مفتاح API من السكرتس
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("مفتاح GROQ_API_KEY غير مضاف في Secrets!")
    st.stop()

client = Groq(api_key=api_key)

tab1, tab2 = st.tabs(["🚀 Fast Lane (توليد تلقائي)", "🛡️ Guarded Lane (إشراف والتداول)"])

with tab1:
    spider_type = st.radio(
        "اختر نوع العنكبوت:",
        ["Affiliate Spider", "Media Spider", "Digital Products Spider"]
    )
    
    task_desc = st.text_area("وصف المهمة أو المنتج المستهدف:", height=150)
    
    if st.button("تشغيل العنكبوت 🚀"):
        if not task_desc:
            st.warning("رجاء أدخل وصف المهمة أولاً!")
        else:
            with st.spinner(f"جاري تشغيل {spider_type}..."):
                system_prompt = f"أنت عنصر ذكاء اصطناعي خبير باسم {spider_type}. قُم بتحليل الطلب وتوليد مخرجات استراتيجية، سكريبتات إعلانية، ونصوص تسويقية بدقة عالية."
                
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": task_desc}
                        ],
                        temperature=0.7
                    )
                    
                    output_text = response.choices[0].message.content
                    st.success("تم تنفيذ المهمة بنجاح!")
                    st.markdown("### 📊 المخرجات والتحليل:")
                    st.write(output_text)
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التوليد: {e}")

with tab2:
    st.subheader("إشراف التداول (Human-In-The-Loop)")
    st.info("يتم إيقاف الصفقة هنا تلقائياً لانتظار موافقتك البشرية قبل التنفيذ.")
    st.markdown("#### 📈 صفقة قيد الانتظار: BTC/USDT")
    st.write("السعر الحالي: **$64,250** | الإشارة: **BUY (شراء)**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ موافقة وتنفيذ الصفقة"):
            st.success("تم تنفيذ الصفقة بنجاح!")
    with col2:
        if st.button("❌ رفض وإلغاء"):
            st.warning("تم إلغاء الصفقة.")
