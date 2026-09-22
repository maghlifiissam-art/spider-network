from pathlib import Path
import json, sys
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publish_contracts import PLATFORMS
from publish_spider import PublishSpider, job_from_media_handoff, load_policy

st.set_page_config(page_title="Publish Spider", page_icon="📡", layout="wide")
st.markdown("""<style>
.ar { direction: rtl; unicode-bidi: plaintext; text-align: right; letter-spacing: normal !important; word-spacing: normal !important; font-family: Arial, 'Noto Sans Arabic', sans-serif; }
</style>""", unsafe_allow_html=True)
st.title("📡 Publish Spider - وكيل النشر")
policy = load_policy()
a, b, c = st.columns(3)
a.metric("Contract", "publish.v1")
b.metric("Mode", "DRY RUN 🧪" if policy.dry_run else "LIVE 🚀")
c.metric("Platforms", len(PLATFORMS))
st.caption(f"YouTube privacy: {policy.youtube_privacy} | TikTok mode: {policy.tiktok_mode}")

st.subheader("جرب job من fixtures (offline)")
if st.button("شغل job تجريبي"):
    fixture = json.loads((Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "publish_job.json").read_text(encoding="utf-8"))
    receipts = PublishSpider(policy).run_job(fixture)
    for r in receipts:
        st.write(f"**{r['platform']}** → {r['status']} — {r['detail']}")

st.subheader("آخر الإيصالات")
receipts_path = Path("data/publish_receipts.json")
if receipts_path.exists():
    receipts = json.loads(receipts_path.read_text(encoding="utf-8"))
    st.dataframe(receipts[-50:], use_container_width=True)
else:
    st.info("مازال ماكان حتى إيصال.")

st.subheader("الربط (مرة وحدة لكل منصة)")
st.markdown('<div class="ar">', unsafe_allow_html=True)
st.code("python scripts/auth_youtube.py\npython scripts/auth_meta.py\npython scripts/auth_tiktok.py", language=None)
st.markdown("الأسرار كتمشي لـ .env المحلي فقط — ممنوعة من git.", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
