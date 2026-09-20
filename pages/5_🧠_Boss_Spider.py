"""
pages/5_🧠_Boss_Spider.py
---------------------------
مركز القيادة: هنا كتكتب أي أمر بلغة طبيعية، والعقل المدبر (boss_spider.py)
كيفهمو ويوزعو على الوكيل المناسب. هذا خاص بيك نتا (المالك) — ماشي واجهة
الزبناء (تلك كاينة فـ whatsapp_bot.py، مخصصة غير للبيع/الأسئلة).

أمثلة أوامر يمكن تكتبها:
  - "سولي كتاب على تربية الدجاج فالمغرب، 6 فصول، وبيعو ب5 دولار"
  - "ولد ملصق تسويقي على مجموعة منتجات العناية بالبشرة، ستايل عصري"
  - "بغيت قصة مصورة لطفل صغير كيكتشف الفضاء، 8 لوحات، بالفرنسية"
  - "شنو خرلي فالسوق ديال الأفلييت اليوم؟"
  - "شنو المنتجات اللي نشرتهم لحد الآن؟"
"""

import streamlit as st
from boss_spider import handle_command

st.set_page_config(page_title="Boss Spider — مركز القيادة", page_icon="🧠", layout="wide")
st.title("🧠 Boss Spider — العقل المدبر")
st.caption("اكتب أي أمر بلغة طبيعية، وهو كيوجهو للوكيل المناسب (كتب، قصص مصورة، ملصقات، تسويق، أخبار...)")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("Groq API Key", type="password", value=st.secrets.get("GROQ_API_KEY", ""))
    language = st.selectbox("اللغة", ["العربية", "Français", "English"])
    st.info("💡 قول فالأمر نفسو 'بيعو' ولا 'بلا نشر' باش تحدد واش بغيتي التنفيذ الكامل (توليد + نشر) ولا غير معاينة.")

if "boss_history" not in st.session_state:
    st.session_state.boss_history = []

if not api_key:
    st.warning("دخل Groq API Key من الشريط الجانبي.")
    st.stop()

import os
os.environ["GROQ_API_KEY"] = api_key

command = st.text_area("✍️ الأمر ديالك", placeholder="مثال: سولي كتاب على تربية الدجاج، 6 فصول، وبيعو ب5 دولار", height=100)

if st.button("🚀 نفذ الأمر", use_container_width=True):
    if not command.strip():
        st.error("خاصك تكتب أمر.")
    else:
        with st.spinner("العقل المدبر خدام... (ممكن ياخذ شي دقيقة إيلا كان توليد صور)"):
            result = handle_command(command, language=language, groq_api_key=api_key)

        if result["success"]:
            st.success("✅ تم")
        else:
            st.error("❌ صرا مشكل")
        st.markdown(result["message"])

        st.session_state.boss_history.append({"command": command, "result": result["message"]})

if st.session_state.boss_history:
    st.divider()
    with st.expander(f"📜 سجل الأوامر ({len(st.session_state.boss_history)})"):
        for i, entry in enumerate(reversed(st.session_state.boss_history), 1):
            st.markdown(f"**{i}. الأمر:** {entry['command']}")
            st.markdown(entry["result"])
            st.markdown("---")
