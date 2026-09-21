"""
pages/6_📊_Dashboard.py
---------------------------
لوحة التحكم الشاملة ديال Spider Network:
  1. حالة كل خط إنتاج (كتب/قصص مصورة/كتب تلوين/ملصقات/شعارات) — عدد
     العمليات الناجحة والفاشلة
  2. سجل مباشر لآخر العمليات (نجاح/فشل/أي حركة) بالتفصيل
  3. عداد الأرباح الحقيقي من Gumroad: الإيراد الإجمالي، عمولة Gumroad
     المقتطعة، الضرائب، صافي الربح، وعدد العمليات المقتنصة بنجاح
  4. فهرس كل المنتجات المنشورة لحد الآن
"""

import streamlit as st

from ops_log import get_stats, get_recent
from gumroad_reports import get_earnings_report
from catalog import load_catalog

st.set_page_config(page_title="لوحة التحكم — Spider Network", page_icon="📊", layout="wide")
from rtl_support import inject_rtl
inject_rtl()
st.title("📊 لوحة التحكم الشاملة")

LINE_LABELS = {
    "book": "📖 الكتب",
    "comic": "🖼️ القصص المصورة",
    "coloring_book": "🎨 كتب التلوين",
    "poster": "🖼️ الملصقات",
    "logo": "🏷️ الشعارات",
    "marketing": "📢 المحتوى التسويقي",
    "news_blog": "📰 التدوينات/الأخبار",
    "engineering": "⚙️ الهندسة/القطع",
    "electronics": "🔌 الإلكترونيات",
    "cloud": "☁️ البنية السحابية",
    "monitor": "🔍 الرصد الآلي",
}

tab1, tab2, tab3 = st.tabs(["🏭 خطوط الإنتاج", "💰 الأرباح والاقتطاعات", "🗂️ فهرس المنتجات"])

# ---------------------------------------------------------------------------
# تبويب 1: حالة كل خط إنتاج + سجل العمليات
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("حالة كل خط إنتاج")
    stats = get_stats()
    cols = st.columns(4)
    for i, (line, data) in enumerate(stats.items()):
        if data["total"] == 0:
            continue
        with cols[i % 4]:
            label = LINE_LABELS.get(line, line)
            st.metric(label, f"{data['success']}/{data['total']}", f"{data['failed']} فشل" if data["failed"] else "0 فشل")

    st.divider()
    st.subheader("📜 آخر العمليات")
    recent = get_recent(50)
    if not recent:
        st.info("ماكاينش شي عملية مسجلة بعد.")
    else:
        for entry in recent:
            icon = "✅" if entry["status"] == "success" else "❌"
            line_label = LINE_LABELS.get(entry["line"], entry["line"])
            ts = entry["timestamp"][:16].replace("T", " ")
            with st.expander(f"{icon} {ts} — {line_label} — {entry.get('product_name', '')}"):
                st.write(entry.get("message", ""))

# ---------------------------------------------------------------------------
# تبويب 2: الأرباح والاقتطاعات (من Gumroad مباشرة — بيانات حقيقية)
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("💰 تقرير الأرباح (من Gumroad مباشرة)")
    after_date = st.date_input("عرض المبيعات من تاريخ:", value=None)
    after_str = after_date.isoformat() if after_date else None

    if st.button("🔄 تحديث التقرير"):
        with st.spinner("كنجيبو البيانات من Gumroad..."):
            report = get_earnings_report(after_str)

        if not report["success"]:
            st.error(f"❌ فشل جلب البيانات: {report['error']}")
        else:
            s = report["summary"]
            c1, c2, c3 = st.columns(3)
            c1.metric("عدد العمليات المقتنصة بنجاح", s["successful_operations"], f"من أصل {s['total_operations']}")
            c2.metric("الإيراد الإجمالي", f"${s['gross_cents']/100:.2f}")
            c3.metric("💵 صافي الربح", f"${s['net_cents']/100:.2f}")

            c4, c5, c6 = st.columns(3)
            c4.metric("عمولة Gumroad المقتطعة", f"${s['gumroad_fee_cents']/100:.2f}")
            c5.metric("الضرائب المقتطعة", f"${s['tax_cents']/100:.2f}")
            c6.metric("استردادات / منازعات", f"{s['refunded_count']} / {s['chargedback_count']}")

            st.divider()
            st.subheader("تفاصيل كل عملية بيع")
            for sale in report["sales"]:
                status = "🔴 مسترجعة" if sale.get("refunded") else ("🟠 منازعة" if sale.get("chargedback") else "🟢 ناجحة")
                st.write(
                    f"{status} — **{sale.get('product_name')}** — "
                    f"${sale.get('price', 0)/100:.2f} (عمولة: ${sale.get('gumroad_fee', 0)/100:.2f}) — "
                    f"{sale.get('created_at', '')[:16].replace('T', ' ')}"
                )
    else:
        st.info("اضغط 'تحديث التقرير' باش تجيب آخر بيانات المبيعات من Gumroad.")

# ---------------------------------------------------------------------------
# تبويب 3: فهرس كل المنتجات
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("🗂️ كل المنتجات المنشورة")
    catalog = load_catalog()
    if not catalog:
        st.info("ماكاينش شي منتج فالفهرس بعد.")
    else:
        for p in reversed(catalog):
            st.markdown(
                f"**{p['name']}** ({LINE_LABELS.get(p['type'], p['type'])}) — "
                f"${p['price_cents']/100:.2f} — [رابط الشراء]({p['buy_link']}) — "
                f"{p['published_at'][:16].replace('T', ' ')}"
            )
