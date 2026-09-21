from pathlib import Path
import base64, json, sys
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from media_spider import MediaSpider, OfflineAdapter
st.set_page_config(page_title="Media Spider", page_icon="🎬", layout="wide")
st.markdown("""<style>
.ar { direction: rtl; unicode-bidi: plaintext; text-align: right; letter-spacing: normal !important; word-spacing: normal !important; font-family: Arial, 'Noto Sans Arabic', sans-serif; }
</style>""", unsafe_allow_html=True)
st.title("🎬 Media Spider - Nexa Stories")
banner_path = Path(__file__).resolve().parents[1] / "assets" / "media_arabic_banner.png"
banner_b64 = base64.b64encode(banner_path.read_bytes()).decode("ascii")
st.markdown(f'<img src="data:image/png;base64,{banner_b64}" style="width:100%;height:auto" alt="سيف بن ذي يزن: التاريخ ثم السيرة الشعبية">', unsafe_allow_html=True)
result=MediaSpider(OfflineAdapter(Path(__file__).resolve().parents[1]/'fixtures')).run_pilot()
a,b,c,d=st.columns(4)
a.metric("Contract",result['contract_version']); b.metric("Subagents",len(result['stages'])); c.metric("Derivatives",result['pilot']['derivatives']); d.metric("Publish","Disabled")
st.subheader("Sayf ibn Dhi Yazan - history and folk epic")
st.status("Final review draft - publishing disabled", state="complete")
st.code(" -> ".join(result['stages']), language=None)
st.subheader("Quality gates")
st.json({"qa_decision":result['qa_decision'],"publish_allowed":result['publish_allowed'],"zero_cost":result['zero_cost'],"phone_app_dependency":False})
st.subheader("Evidence")
for claim in result['claims']:
    with st.expander(f"{claim['kind']} - {claim['confidence']:.0%}"):
        st.write(claim['text']); st.code(claim['source_url']); st.caption(claim['observed_at'])
