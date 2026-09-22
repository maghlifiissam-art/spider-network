"""Sales Spider review page: lead queue, reply drafts, deals, attribution, commissions.

Everything here is a local draft review. This page never sends messages,
publishes anything, or touches payment settings.
"""
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rtl_support import inject_rtl  # noqa: E402
from sales_spider import OfflineAdapter, SalesSpider  # noqa: E402

st.set_page_config(page_title="Sales Spider", page_icon="🤝", layout="wide")
inject_rtl()
st.markdown("""<style>
* { letter-spacing: normal !important; word-spacing: normal !important; }
table { direction: rtl; }
.ar { direction: rtl; unicode-bidi: plaintext; text-align: right;
      font-family: Arial, 'Noto Sans Arabic', sans-serif; }
</style>""", unsafe_allow_html=True)
st.markdown('<h1 class="ar">🤝 Sales Spider — مراجعة المبيعات</h1>',
            unsafe_allow_html=True)
st.markdown(
    '<p class="ar">وكيل تأكيد المبيعات: تصفية الزبائن، اقتراح الردود، توثيق الصفقات، '
    "الإسناد والعمولات. ما كيرسل والو بوحدو — كل رد مسودة حتى توافق عليه.</p>",
    unsafe_allow_html=True,
)


def md_table(rows):
    """Render a list of dicts as a plain Markdown table (no pyarrow dependency)."""
    if not rows:
        return "_\u0644\u0627 \u0634\u064a\u0621._"
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)

result = SalesSpider(adapter=OfflineAdapter(ROOT / "fixtures"),
                     state_dir=ROOT / "state" / "sales").run_pilot()

c1, c2, c3, c4 = st.columns(4)
c1.metric("زبائن مؤهلون", len(result["qualified_leads"]))
c2.metric("مرفوضون (بلا مصدر/منتج)", len(result["rejected_leads"]))
c3.metric("مسودات الردود", len(result["reply_drafts"]))
won = [o for o in result["outcomes"] if o["status"] == "won"]
c4.metric("صفقات مؤكدة الأداء", len(won))

st.divider()
st.markdown('<h2 class="ar">📥 الردود المقترحة (مسودات فقط)</h2>',
            unsafe_allow_html=True)
st.markdown(
    '<p class="ar">راجع كل رد: بغيتو كما هو، بدلو، ولا رفضو. '
    "ما غادي يتصيفط حتى شيء من هنا.</p>",
    unsafe_allow_html=True,
)
if "draft_decisions" not in st.session_state:
    st.session_state.draft_decisions = {}
for draft in result["reply_drafts"]:
    with st.expander(f"{draft['draft_id']} → {draft['lead_id']} ({draft['objection_id'] or 'بدون اعتراض'})"):
        edited = st.text_area("الرد", value=draft["body"], key=f"body-{draft['draft_id']}", height=120)
        decision = st.radio(
            "القرار", ["قيد المراجعة", "مقبول (للإرسال اليدوي فقط)", "مرفض"],
            key=f"dec-{draft['draft_id']}", horizontal=True,
        )
        st.session_state.draft_decisions[draft["draft_id"]] = {
            "decision": decision, "body": edited,
        }
        st.markdown('<p class="ar">⚠️ القبول هنا ما كيرسلش — الإرسال كيتم يدوياً من عندك فقط.</p>',
                    unsafe_allow_html=True)

st.divider()
left, right = st.columns(2)
with left:
    st.markdown('<h2 class="ar">🧾 الصفقات</h2>', unsafe_allow_html=True)
    st.markdown(md_table(result["outcomes"]))
    st.markdown('<h2 class="ar">💰 العمولات</h2>', unsafe_allow_html=True)
    st.markdown(md_table(result["commissions"]))
with right:
    st.markdown('<h2 class="ar">🧭 الإسناد (مصدر كل زبون)</h2>', unsafe_allow_html=True)
    st.markdown(md_table(result["attribution"]))
    st.markdown('<h2 class="ar">🚫 المرفوضون</h2>', unsafe_allow_html=True)
    st.markdown(md_table(result["rejected_leads"]))

st.divider()
st.markdown(
    f'<p class="ar">العقد: {result["contract_version"]} | القرار: {result["qa_decision"]} | '
    f"التسليم: {', '.join(result['handoff_targets'])} | "
    "الإرسال التلقائي: 🔴 مقفل | النشر: 🔴 مقفل</p>",
    unsafe_allow_html=True,
)
