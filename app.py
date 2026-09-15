import streamlit as st
import os

# 1. إعداد الصفحة
st.set_page_config(
    page_title="Spider Network Dashboard",
    page_icon="🕷️",
    layout="wide"
)

# 2. قراءة المفاتيح وحالة البيئة
def get_secret(key_name, default=""):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return os.getenv(key_name, default)

# 3. القائمة الجانبية (Sidebar)
st.sidebar.title("🕷️ Spider Network Control")
st.sidebar.markdown("---")

st.sidebar.subheader("📊 إحصائيات النظام")
col_sb1, col_sb2 = st.sidebar.columns(2)
col_sb1.metric("العناكب النشطة", "4")
col_sb2.metric("الحالة", "✅ جاهز")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ التحكم في الأداء")
rate_limit = st.sidebar.slider("LLM Rate Limit (مكالمة/دقيقة)", 5, 60, 20)

# 4. الواجهة الرئيسية
st.title("🕷️ غرفة عمليات شبكة العناكب")

tab_fast, tab_guarded, tab_logs = st.tabs([
    "🚀 Fast Lane (توليد تلقائي)", 
    "🛡️ Guarded Lane (التداول والإشراف)", 
    "📜 السجلات والتقارير"
])

# --- TAB 1: Fast Lane ---
with tab_fast:
    st.subheader("اقتناص الفرص والمحتوى السريع")
    spider_type = st.radio("اختر نوع العنكبوت:", ["Affiliate Spider", "Media Spider", "Digital Products Spider"], horizontal=True)
    
    prompt_input = st.text_area("وصف المهمة أو المنتج المستهدف:", placeholder="مثال: اقتناص منتج موضة عالمي وإعداد سكريبت إعلاني...")
    
    if st.button("تشغيل العنكبوت 🚀"):
        if prompt_input:
            st.info(f"جاري تشغيل {spider_type}...")
            st.success("تم تنفيذ المهمة بنجاح!")
            st.json({
                "status": "success",
                "spider": spider_type,
                "output": "تم توليد المحتوى ورابط الأفلييت بنجاح."
            })
        else:
            st.warning("يرجى إدخال وصف المهمة أولاً.")

# --- TAB 2: Guarded Lane ---
with tab_guarded:
    st.subheader("إشراف التداول (Human-In-The-Loop)")
    st.info("يتم إيقاف الصفقة هنا تلقائياً لانتظار موافقتك البشرية قبل التنفيذ.")
    
    with st.container():
        st.markdown("### 📈 صفقة قيد الانتظار: BTC/USDT")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("السعر الحالي", "$64,250")
        col2.metric("الإشارة", "BUY (شراء)")
        col3.metric("الهدف", "$66,000")
        col4.metric("إيقاف الخسارة", "$63,100")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ موافقة وتنفيذ الصفقة", use_container_width=True):
                st.success("تم إرسال أمر التنفيذ للمنصة!")
        with col_btn2:
            if st.button("❌ رفض وإلغاء", use_container_width=True):
                st.error("تم إلغاء الصفقة بنجاح وحماية الرصيد.")

# --- TAB 3: Logs ---
with tab_logs:
    st.subheader("سجل العمليات اللحظي")
    st.code("System initialized successfully...\n[INFO] Streamlit Cloud connected.\n[INFO] Spiders ready for execution.", language="bash")
