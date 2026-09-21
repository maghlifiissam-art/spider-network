"""Read-only Market Spy interface with explicit provenance and proxy labels."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from market_spy_spider import research_market

st.set_page_config(page_title="Market Spy", page_icon="🕵️", layout="wide")
from rtl_support import inject_rtl
inject_rtl()
st.title("🕵️ Market Spy - رادار السوق")
st.caption("مؤشرات سوق موثقة حسب المجال والجغرافيا. الترتيب والبحث proxies، ماشي مبيعات مؤكدة.")
query = st.text_input("المجال أو المنتج", placeholder="مثال: AI photo editor")
geography = st.text_input("الدولة (ISO)", value="US", max_chars=2).upper()
category = st.selectbox("الفئة", ["Auto", "digital_product", "ebook", "design_asset", "wall_art_decor", "sticker", "logo", "children_coloring_book", "illustrated_story", "physical_product"])
if st.button("🔎 حلل السوق", use_container_width=True):
    if not query.strip():
        st.error("دخل مجال أو منتج.")
    else:
        with st.spinner("كنجمع المؤشرات العامة بمعدل محافظ..."):
            report = research_market(query.strip(), geography, market_category=None if category == "Auto" else category)
        if not report["opportunities"]:
            st.warning("ما لقيناش مؤشرات عامة مطابقة. ما اخترعنا حتى رقم ناقص.")
        for item in report["opportunities"][:10]:
            with st.container(border=True):
                st.subheader(f"{item['product']} - {item['opportunity_score']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("الجغرافيا", item["geography"])
                c2.metric("الثقة", f"{item['confidence']:.0%}")
                c3.metric("مبيعات مؤكدة", "نعم" if item["is_verified_sales"] else "لا")
                st.write(f"**Metric / proxy:** {item['metric_or_proxy']}")
                for url in item["source_urls"]:
                    st.markdown(f"[المصدر]({url})")
                st.caption(" | ".join(item["limitations"]))
        with st.expander("البيانات المنظمة والمصادر"):
            st.json(report)
        st.download_button("تنزيل JSON", data=json.dumps(report, ensure_ascii=False, indent=2), file_name="market-spy-report.json", mime="application/json")
